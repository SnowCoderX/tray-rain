# -*- coding: utf-8 -*-
import json
import logging
import os
import threading
import warnings
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFont
import pystray

try:
    from requests import RequestsDependencyWarning
except Exception:  # pragma: no cover
    RequestsDependencyWarning = None

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
LOG_PATH = os.path.join(os.path.dirname(__file__), "tray-rain.log")

DEFAULT_CONFIG = {
    "latitude": 55.7558,
    "longitude": 37.6176,
    "timezone": "Europe/Moscow",
    "units": "celsius",
    "refresh_minutes": 20,
    "rain_threshold_mm": 0.1,
    "show_debug_console": False,
    "force_rain_later": None,
    "force_temp": None,
}

WEATHER_CODE_TEXT = {
    0: "Ясно",
    1: "В основном ясно",
    2: "Переменная облачность",
    3: "Пасмурно",
    45: "Туман",
    48: "Изморозь",
    51: "Слабая морось",
    53: "Морось",
    55: "Сильная морось",
    56: "Ледяная морось",
    57: "Ледяная морось",
    61: "Слабый дождь",
    63: "Дождь",
    65: "Сильный дождь",
    66: "Ледяной дождь",
    67: "Ледяной дождь",
    71: "Слабый снег",
    73: "Снег",
    75: "Сильный снег",
    77: "Снежные зерна",
    80: "Ливни",
    81: "Ливни",
    82: "Сильные ливни",
    85: "Снегопады",
    86: "Снегопады",
    95: "Гроза",
    96: "Гроза",
    99: "Гроза",
}


def setup_logging(cfg):
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.info("Tray Rain starting. PID=%s", os.getpid())
    logging.info("Config: %s", cfg)

    if RequestsDependencyWarning is not None:
        warnings.filterwarnings("ignore", category=RequestsDependencyWarning)

    if cfg.get("show_debug_console"):
        print("Tray Rain is running. Check the hidden tray icons (^) if you don't see it.")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(raw)
    return cfg


def get_tzinfo(name):
    if ZoneInfo is None:
        return None
    try:
        return ZoneInfo(name)
    except Exception:
        return None


def text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_droplet(draw, center_x, center_y, size, color):
    top = center_y - size
    left = center_x - size // 2
    right = center_x + size // 2
    bottom = center_y + size
    draw.ellipse((left, center_y - size // 3, right, bottom), fill=color)
    draw.polygon(
        [(center_x, top), (left, center_y - size // 4), (right, center_y - size // 4)],
        fill=color,
    )


def load_font(size):
    try:
        return ImageFont.truetype("C:\\Windows\\Fonts\\segoeui.ttf", size)
    except Exception:
        return ImageFont.load_default()


def build_icon(temp_c, rain_later):
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bg = (40, 118, 210, 255) if rain_later else (70, 170, 110, 255)
    draw.ellipse((4, 4, size - 4, size - 4), fill=bg)

    if temp_c is None:
        text = "?"
    else:
        text = f"{int(round(temp_c))}"

    font = load_font(28)
    text_w, text_h = text_size(draw, text, font)
    draw.text(
        ((size - text_w) / 2, (size - text_h) / 2 - 2),
        text,
        font=font,
        fill=(255, 255, 255, 255),
    )

    if rain_later:
        drop_color = (210, 230, 255, 255)
        draw_droplet(draw, 48, 18, 12, drop_color)

    return img.resize((32, 32), Image.LANCZOS)


def weather_text(code):
    if code is None:
        return "Погода"
    return WEATHER_CODE_TEXT.get(int(code), "Погода")


def parse_hour_time(text, tz):
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None and tz is not None:
        dt = dt.replace(tzinfo=tz)
    return dt


def fetch_weather(cfg):
    params = {
        "latitude": cfg["latitude"],
        "longitude": cfg["longitude"],
        "current": "temperature_2m,weather_code,precipitation",
        "hourly": "precipitation,weather_code,temperature_2m",
        "daily": "precipitation_sum",
        "timezone": cfg["timezone"],
    }
    r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=12)
    r.raise_for_status()
    data = r.json()

    current = data.get("current", {})
    temp = current.get("temperature_2m")
    code = current.get("weather_code")

    tz = get_tzinfo(cfg["timezone"])
    now = datetime.now(tz) if tz else datetime.now()
    today = now.date().isoformat()

    rain_later = False
    next_rain = None
    threshold = float(cfg.get("rain_threshold_mm", 0.1))

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    precip = hourly.get("precipitation", [])

    for t, p in zip(times, precip):
        if not t.startswith(today):
            continue
        if p is None or float(p) < threshold:
            continue
        hour_dt = parse_hour_time(t, tz)
        if hour_dt <= now:
            continue
        rain_later = True
        next_rain = hour_dt
        break

    if cfg.get("force_rain_later") is not None:
        rain_later = bool(cfg.get("force_rain_later"))
        next_rain = now

    if cfg.get("force_temp") is not None:
        temp = cfg.get("force_temp")

    return {
        "temp": temp,
        "code": code,
        "rain_later": rain_later,
        "next_rain": next_rain,
        "updated_at": now,
    }


def format_title(info):
    if info is None:
        return "Погода: нет данных"
    temp = info.get("temp")
    code = info.get("code")
    rain_later = info.get("rain_later")

    temp_text = "?C" if temp is None else f"{int(round(temp))}C"
    condition = weather_text(code)
    rain_text = "Дождь позже сегодня" if rain_later else "Дождя позже сегодня нет"
    return f"{temp_text} {condition} | {rain_text}"


def format_menu_lines(info, last_error):
    if last_error:
        return "Ошибка", last_error
    if info is None:
        return "Нет данных", "Жду обновления..."

    temp = info.get("temp")
    code = info.get("code")
    rain_later = info.get("rain_later")
    next_rain = info.get("next_rain")
    updated_at = info.get("updated_at")

    temp_text = "?C" if temp is None else f"{int(round(temp))}C"
    line1 = f"Сейчас: {temp_text}, {weather_text(code)}"
    if rain_later and next_rain is not None:
        line2 = f"Позже сегодня: дождь в {next_rain.strftime('%H:%M')}"
    else:
        line2 = "Позже сегодня: дождя не ожидается"
    line3 = f"Обновлено: {updated_at.strftime('%H:%M')}"
    return line1, f"{line2} | {line3}"


def main():
    cfg = load_config()
    setup_logging(cfg)

    state = {
        "info": None,
        "error": None,
        "line1": "Запуск...",
        "line2": "",
    }
    lock = threading.Lock()
    stop_event = threading.Event()

    def refresh():
        try:
            info = fetch_weather(cfg)
            title = format_title(info)
            with lock:
                state["info"] = info
                state["error"] = None
                state["line1"], state["line2"] = format_menu_lines(info, None)
            icon.icon = build_icon(info.get("temp"), info.get("rain_later"))
            icon.title = title
        except Exception as exc:
            logging.exception("Refresh failed")
            with lock:
                state["error"] = str(exc)
                state["line1"], state["line2"] = format_menu_lines(None, str(exc))
            icon.title = "Погода: ошибка"
        icon.update_menu()

    def refresh_loop():
        refresh()
        while not stop_event.wait(float(cfg.get("refresh_minutes", 20)) * 60.0):
            refresh()

    def on_refresh(icon_obj, item):
        refresh()

    def on_open_config(icon_obj, item):
        os.startfile(CONFIG_PATH)

    def on_open_log(icon_obj, item):
        os.startfile(LOG_PATH)

    def on_quit(icon_obj, item):
        stop_event.set()
        icon_obj.stop()

    def menu_line1(_item):
        with lock:
            return state["line1"]

    def menu_line2(_item):
        with lock:
            return state["line2"]

    menu = pystray.Menu(
        pystray.MenuItem(menu_line1, None, enabled=False),
        pystray.MenuItem(menu_line2, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Обновить", on_refresh),
        pystray.MenuItem("Открыть настройки", on_open_config),
        pystray.MenuItem("Открыть лог", on_open_log),
        pystray.MenuItem("Выход", on_quit),
    )

    icon = pystray.Icon("tray-rain", title="Погода", icon=build_icon(None, False), menu=menu)

    def setup(icon_obj):
        icon_obj.visible = True
        threading.Thread(target=refresh_loop, daemon=True).start()

    icon.run(setup=setup)


if __name__ == "__main__":
    main()
