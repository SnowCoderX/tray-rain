# -*- coding: utf-8 -*-
import json
import logging
import os
import sys
import threading
import warnings
from datetime import datetime, timedelta

import requests
from PIL import Image, ImageDraw, ImageFont
import pystray
import webview

try:
    from requests import RequestsDependencyWarning
except Exception:  # pragma: no cover
    RequestsDependencyWarning = None

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None

def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    return os.path.join(base, name)

APP_DIR = app_dir()

CONFIG_PATH = os.path.join(APP_DIR, "config.json")
LOG_PATH = os.path.join(APP_DIR, "tray-rain.log")
MAP_HTML_PATH = resource_path("map.html")
APP_NAME = "Tray Rain"
__version__ = "1.4"
REPO_URL = "https://github.com/SnowCoderX/tray-rain"
RELEASES_URL = f"{REPO_URL}/releases"

DEFAULT_CONFIG = {
    "latitude": 55.7558,
    "longitude": 37.6176,
    "timezone": "Europe/Moscow",
    "units": "celsius",
    "language": "en",
    "refresh_minutes": 20,
    "rain_threshold_mm": 0.1,
    "show_debug_console": False,
    "force_rain_later": None,
    "force_temp": None,
}

LANG_STRINGS = {
    "ru": {
        "weather_title": "Погода",
        "weather_no_data": "Погода: нет данных",
        "weather_error": "Погода: ошибка",
        "weather_generic": "Погода",
        "rain_now_until": "Дождь сейчас до {time}",
        "rain_now": "Дождь сейчас",
        "rain_at": "Дождь в {time}",
        "rain_range": "Дождь {start}-{end}",
        "rain_later_none": "Дождя позже сегодня нет",
        "menu_error": "Ошибка",
        "menu_no_data": "Нет данных",
        "menu_waiting": "Жду обновления...",
        "menu_now": "Сейчас: {temp}, {condition}",
        "menu_rain_now_until": "Сейчас дождь до {time}",
        "menu_rain_now": "Сейчас дождь",
        "menu_rain_later": "Позже сегодня: дождь {blocks}",
        "menu_rain_later_none": "Позже сегодня: дождя не ожидается",
        "menu_updated": "Обновлено: {time}",
        "menu_intervals": "Интервалы дождя",
        "menu_choose_map": "Выбрать локацию на карте",
        "menu_refresh": "Обновить",
        "menu_open_config": "Открыть настройки",
        "menu_open_log": "Открыть лог",
        "menu_quit": "Выход",
        "menu_language": "Язык",
        "menu_about": "О приложении",
        "menu_releases": "Открыть релизы",
        "menu_version": "Версия {version}",
        "lang_ru": "Русский",
        "lang_en": "English",
        "intervals_none": "Сегодня дождя не ожидается",
        "intervals_next": "далее {blocks}",
        "later_prefix": "позже {block}",
        "blocks_more": "ещё {count}",
        "map_title": "Выбор локации",
        "map_save": "Сохранить координаты",
        "map_status": "Кликните по карте, затем сохраните.",
        "map_status_selected_prefix": "Выбрано: ",
        "map_status_saved": "Сохранено.",
        "map_api_unavailable": "API недоступен. Откройте окно через приложение.",
        "location_saved": "Локация сохранена",
        "invalid_coords": "Некорректные координаты",
        "open_config_failed": "Не удалось открыть настройки",
        "map_not_found": "map.html не найден",
    },
    "en": {
        "weather_title": "Weather",
        "weather_no_data": "Weather: no data",
        "weather_error": "Weather: error",
        "weather_generic": "Weather",
        "rain_now_until": "Rain now until {time}",
        "rain_now": "Rain now",
        "rain_at": "Rain at {time}",
        "rain_range": "Rain {start}-{end}",
        "rain_later_none": "No rain later today",
        "menu_error": "Error",
        "menu_no_data": "No data",
        "menu_waiting": "Waiting for update...",
        "menu_now": "Now: {temp}, {condition}",
        "menu_rain_now_until": "Raining now until {time}",
        "menu_rain_now": "Raining now",
        "menu_rain_later": "Later today: rain {blocks}",
        "menu_rain_later_none": "Later today: no rain expected",
        "menu_updated": "Updated: {time}",
        "menu_intervals": "Rain intervals",
        "menu_choose_map": "Choose location on map",
        "menu_refresh": "Refresh",
        "menu_open_config": "Open settings",
        "menu_open_log": "Open log",
        "menu_quit": "Quit",
        "menu_language": "Language",
        "menu_about": "About",
        "menu_releases": "Open releases",
        "menu_version": "Version {version}",
        "lang_ru": "Russian",
        "lang_en": "English",
        "intervals_none": "No rain expected today",
        "intervals_next": "next {blocks}",
        "later_prefix": "later {block}",
        "blocks_more": "more {count}",
        "map_title": "Select location",
        "map_save": "Save coordinates",
        "map_status": "Click on the map, then save.",
        "map_status_selected_prefix": "Selected: ",
        "map_status_saved": "Saved.",
        "map_api_unavailable": "API unavailable. Open the window from the app.",
        "location_saved": "Location saved",
        "invalid_coords": "Invalid coordinates",
        "open_config_failed": "Failed to open settings",
        "map_not_found": "map.html not found",
    },
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

WEATHER_CODE_TEXT_EN = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Rain showers",
    82: "Violent rain showers",
    85: "Snow showers",
    86: "Snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm",
    99: "Thunderstorm",
}


RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}

def is_rain_code(code):
    try:
        return int(code) in RAIN_CODES
    except Exception:
        return False



def setup_logging(cfg):
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
        errors="replace",
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


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def get_lang(cfg):
    lang = (cfg or {}).get("language", "en")
    return lang if lang in LANG_STRINGS else "en"


def t(lang, key, **kwargs):
    lang = lang if lang in LANG_STRINGS else "en"
    text = LANG_STRINGS.get(lang, {}).get(key, key)
    try:
        return text.format(**kwargs)
    except Exception:
        return text



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


def load_font(size, bold=False):
    font_name = "segoeuib.ttf" if bold else "segoeui.ttf"
    try:
        return ImageFont.truetype(f"C:\\Windows\\Fonts\\{font_name}", size)
    except Exception:
        return ImageFont.load_default()


def load_map_html(lat, lon, lang):
    try:
        with open(MAP_HTML_PATH, "r", encoding="utf-8") as f:
            html = f.read()
    except Exception:
        return None
    return (
        html
        .replace("{{LAT}}", f"{lat}")
        .replace("{{LON}}", f"{lon}")
        .replace("{{LANG}}", lang)
        .replace("{{TITLE}}", t(lang, "map_title"))
        .replace("{{SAVE}}", t(lang, "map_save"))
        .replace("{{STATUS}}", t(lang, "map_status"))
        .replace("{{STATUS_SELECTED_PREFIX}}", t(lang, "map_status_selected_prefix"))
        .replace("{{STATUS_SAVED}}", t(lang, "map_status_saved"))
        .replace("{{STATUS_API_UNAVAILABLE}}", t(lang, "map_api_unavailable"))
    )


class MapApi:
    def __init__(self, on_set):
        self._on_set = on_set

    def set_location(self, lat, lon):
        return self._on_set(lat, lon)


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

    if len(text) <= 1:
        font_size = 34
    elif len(text) == 2:
        font_size = 30
    else:
        font_size = 26

    font = load_font(font_size, bold=True)
    text_w, text_h = text_size(draw, text, font)
    draw.text(
        ((size - text_w) / 2, (size - text_h) / 2 - 2),
        text,
        font=font,
        fill=(255, 255, 255, 255),
        stroke_width=2 if font_size >= 30 else 1,
        stroke_fill=(20, 20, 20, 255),
    )

    if rain_later:
        drop_color = (210, 230, 255, 255)
        draw_droplet(draw, 48, 18, 12, drop_color)

    return img.resize((32, 32), Image.LANCZOS)


def weather_text(code, lang):
    if code is None:
        return t(lang, "weather_generic")
    table = WEATHER_CODE_TEXT_EN if lang == "en" else WEATHER_CODE_TEXT
    return table.get(int(code), t(lang, "weather_generic"))



def parse_hour_time(text, tz):
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None and tz is not None:
        dt = dt.replace(tzinfo=tz)
    return dt

def build_rain_blocks(hours):
    blocks = []
    if not hours:
        return blocks
    start = hours[0]
    last = start
    for hour_dt in hours[1:]:
        if hour_dt == last + timedelta(hours=1):
            last = hour_dt
        else:
            blocks.append((start, last + timedelta(hours=1)))
            start = hour_dt
            last = hour_dt
    blocks.append((start, last + timedelta(hours=1)))
    return blocks


def format_blocks(blocks, lang, max_blocks=2):
    if not blocks:
        return ""
    shown = blocks[:max_blocks]
    parts = [f"{s.strftime('%H:%M')}-{e.strftime('%H:%M')}" for s, e in shown]
    extra = len(blocks) - len(shown)
    if extra > 0:
        parts.append(t(lang, "blocks_more", count=extra))
    return "; ".join(parts)


def format_blocks_full(blocks):
    if not blocks:
        return ""
    return "\n".join([f"{s.strftime('%H:%M')}-{e.strftime('%H:%M')}" for s, e in blocks])



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
    current_hour = now.replace(minute=0, second=0, microsecond=0)

    threshold = float(cfg.get("rain_threshold_mm", 0.1))

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    precip = hourly.get("precipitation", [])
    codes = hourly.get("weather_code", [])

    candidates = []
    candidate_debug = []
    for idx, (t, p) in enumerate(zip(times, precip)):
        if not t.startswith(today):
            continue
        code_hour = codes[idx] if idx < len(codes) else None
        if code_hour is not None:
            if not is_rain_code(code_hour):
                continue
        else:
            if p is None or float(p) < threshold:
                continue
        hour_dt = parse_hour_time(t, tz)
        if hour_dt < current_hour:
            continue
        candidates.append(hour_dt)
        candidate_debug.append((hour_dt, float(p) if p is not None else None, code_hour))

    blocks = build_rain_blocks(candidates)
    rain_later = bool(blocks)
    rain_now = False
    next_rain = None
    rain_start = None
    rain_end = None

    current_block = None
    for start, end in blocks:
        if start <= current_hour < end:
            current_block = (start, end)
            break

    if current_block:
        rain_now = True
        rain_start, rain_end = current_block
        next_rain = rain_start
    else:
        for start, end in blocks:
            if start >= current_hour:
                rain_start, rain_end = start, end
                next_rain = rain_start
                break

    logging.info(
        "Rain check: now=%s current_hour=%s threshold=%.2f next_rain=%s rain_later=%s rain_now=%s rain_start=%s rain_end=%s blocks=%s candidates=%s",
        now.isoformat(),
        current_hour.isoformat(),
        threshold,
        next_rain.isoformat() if next_rain else None,
        rain_later,
        rain_now,
        rain_start.isoformat() if rain_start else None,
        rain_end.isoformat() if rain_end else None,
        [(s.strftime("%H:%M"), e.strftime("%H:%M")) for s, e in blocks],
        [(d.strftime("%H:%M"), p, c) for d, p, c in candidate_debug],
    )

    if cfg.get("force_rain_later") is not None:
        rain_later = bool(cfg.get("force_rain_later"))
        if rain_later:
            rain_now = True
            rain_start = current_hour
            rain_end = current_hour + timedelta(hours=1)
            next_rain = rain_start
            blocks = [(rain_start, rain_end)]
        else:
            rain_now = False
            rain_start = None
            rain_end = None
            next_rain = None
            blocks = []

    if cfg.get("force_temp") is not None:
        temp = cfg.get("force_temp")

    return {
        "temp": temp,
        "code": code,
        "rain_later": rain_later,
        "rain_now": rain_now,
        "rain_start": rain_start,
        "rain_end": rain_end,
        "rain_blocks": blocks,
        "next_rain": next_rain,
        "updated_at": now,
    }


def format_title(info, lang):
    if info is None:
        return t(lang, "weather_no_data")
    temp = info.get("temp")
    code = info.get("code")
    rain_later = info.get("rain_later")
    rain_start = info.get("rain_start")
    rain_end = info.get("rain_end")
    rain_now = info.get("rain_now")
    blocks = info.get("rain_blocks") or []

    temp_text = "?C" if temp is None else f"{int(round(temp))}C"
    condition = weather_text(code, lang)

    if rain_later and rain_start and rain_end:
        if rain_now:
            rain_text = t(lang, "rain_now_until", time=rain_end.strftime('%H:%M'))
            later_blocks = [b for b in blocks if b[0] >= rain_end]
            if later_blocks:
                s, e = later_blocks[0]
                text = f"{s.strftime('%H:%M')}-{e.strftime('%H:%M')}"
                if len(later_blocks) > 1:
                    text += f" +{len(later_blocks) - 1}"
                rain_text += f", {t(lang, 'later_prefix', block=text)}"
        else:
            rain_text = t(lang, "rain_range", start=rain_start.strftime('%H:%M'), end=rain_end.strftime('%H:%M'))
            later_blocks = [b for b in blocks if b[0] > rain_start]
            if later_blocks:
                s, e = later_blocks[0]
                text = f"{s.strftime('%H:%M')}-{e.strftime('%H:%M')}"
                if len(later_blocks) > 1:
                    text += f" +{len(later_blocks) - 1}"
                rain_text += f", {t(lang, 'later_prefix', block=text)}"
    else:
        rain_text = t(lang, "rain_later_none")

    return f"{temp_text} {condition} | {rain_text}"


def format_menu_lines(info, lang, last_error):
    if last_error:
        return t(lang, "menu_error"), last_error
    if info is None:
        return t(lang, "menu_no_data"), t(lang, "menu_waiting")

    temp = info.get("temp")
    code = info.get("code")
    rain_later = info.get("rain_later")
    rain_end = info.get("rain_end")
    rain_now = info.get("rain_now")
    blocks = info.get("rain_blocks") or []
    updated_at = info.get("updated_at")

    temp_text = "?C" if temp is None else f"{int(round(temp))}C"
    condition = weather_text(code, lang)
    line1 = t(lang, "menu_now", temp=temp_text, condition=condition)

    if rain_later and blocks:
        if rain_now and rain_end:
            line2 = t(lang, "menu_rain_now_until", time=rain_end.strftime('%H:%M'))
            later_blocks = [b for b in blocks if b[0] >= rain_end]
            if later_blocks:
                line2 += f"; {t(lang, 'intervals_next', blocks=format_blocks(later_blocks, lang, max_blocks=2))}"
        else:
            line2 = t(lang, "menu_rain_later", blocks=format_blocks(blocks, lang, max_blocks=2))
    else:
        line2 = t(lang, "menu_rain_later_none")

    line3 = t(lang, "menu_updated", time=updated_at.strftime('%H:%M'))
    return line1, f"{line2} | {line3}"


def main():
    cfg = load_config()
    setup_logging(cfg)

    initial_lang = get_lang(cfg)
    state = {
        "info": None,
        "error": None,
        "line1": t(initial_lang, "menu_waiting"),
        "line2": "",
    }
    lock = threading.Lock()
    stop_event = threading.Event()
    map_window = None
    map_window_lock = threading.Lock()
    keepalive_window = None

    def refresh():
        lang = get_lang(cfg)
        try:
            info = fetch_weather(cfg)
            title = format_title(info, lang)
            with lock:
                state["info"] = info
                state["error"] = None
                state["line1"], state["line2"] = format_menu_lines(info, lang, None)
            icon.icon = build_icon(info.get("temp"), info.get("rain_later"))
            icon.title = title
        except Exception as exc:
            logging.exception("Refresh failed")
            with lock:
                state["error"] = str(exc)
                state["line1"], state["line2"] = format_menu_lines(None, lang, str(exc))
            icon.title = t(lang, "weather_error")
        icon.update_menu()


    def refresh_loop():
        refresh()
        while not stop_event.wait(float(cfg.get("refresh_minutes", 20)) * 60.0):
            refresh()

    def on_refresh(icon_obj, item):
        refresh()

    def on_open_config(icon_obj, item):
        lang = get_lang(cfg)
        try:
            if not os.path.exists(CONFIG_PATH):
                save_config(cfg)
            os.startfile(CONFIG_PATH)
        except Exception as exc:
            logging.exception("Open config failed")
            with lock:
                state["error"] = str(exc)
                state["line1"], state["line2"] = format_menu_lines(None, lang, t(lang, "open_config_failed"))
            icon.title = t(lang, "weather_error")
            icon.update_menu()

    def on_open_log(icon_obj, item):
        os.startfile(LOG_PATH)

    def on_open_releases(icon_obj, item):
        try:
            os.startfile(RELEASES_URL)
        except Exception:
            logging.exception("Open releases failed")

    def intervals_menu_items():
        lang = get_lang(cfg)
        with lock:
            info = state.get("info")
        blocks = info.get("rain_blocks") if info else None
        if not blocks:
            yield pystray.MenuItem(t(lang, "intervals_none"), None, enabled=False)
            return
        for start, end in blocks:
            yield pystray.MenuItem(f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}", None, enabled=False)

    def update_ui_for_language():
        lang = get_lang(cfg)
        with lock:
            info = state.get("info")
            error = state.get("error")
        if error:
            with lock:
                state["line1"], state["line2"] = format_menu_lines(None, lang, error)
            icon.title = t(lang, "weather_error")
        elif info:
            with lock:
                state["line1"], state["line2"] = format_menu_lines(info, lang, None)
            icon.title = format_title(info, lang)
        else:
            with lock:
                state["line1"], state["line2"] = format_menu_lines(None, lang, None)
            icon.title = t(lang, "weather_no_data")
        icon.update_menu()

    def set_language(new_lang):
        cfg["language"] = new_lang
        save_config(cfg)
        update_ui_for_language()

    def lang_checked(lang_value):
        return lambda _item: get_lang(cfg) == lang_value


    def on_set_location(lat, lon):
        lang = get_lang(cfg)
        try:
            cfg["latitude"] = float(lat)
            cfg["longitude"] = float(lon)
        except Exception:
            return {"ok": False, "message": t(lang, "invalid_coords")}
        save_config(cfg)
        refresh()
        return {"ok": True, "message": t(lang, "location_saved")}

    def on_map_closed():
        nonlocal map_window
        map_window = None

    def ensure_map_window():
        nonlocal map_window
        lang = get_lang(cfg)
        html = load_map_html(cfg.get("latitude"), cfg.get("longitude"), lang)
        if not html:
            err = t(lang, "map_not_found")
            with lock:
                state["error"] = err
                state["line1"], state["line2"] = format_menu_lines(None, lang, err)
            icon.title = t(lang, "weather_error")
            icon.update_menu()
            return None

        if map_window is None:
            map_window = webview.create_window(
                t(lang, "map_title"),
                html=html,
                width=540,
                height=600,
                resizable=True,
                js_api=MapApi(on_set_location),
            )
            try:
                map_window.events.closed += on_map_closed
            except Exception:
                pass
        else:
            try:
                map_window.load_html(html)
            except Exception:
                pass
        return map_window

    def on_open_map(icon_obj, item):
        with map_window_lock:
            window = ensure_map_window()
            if not window:
                return
            try:
                window.show()
            except Exception:
                pass

    def on_quit(icon_obj, item):
        stop_event.set()
        icon_obj.stop()
        try:
            if map_window is not None:
                map_window.destroy()
            if keepalive_window is not None:
                keepalive_window.destroy()
        except Exception:
            pass

    def menu_line1(_item):
        with lock:
            return state["line1"]

    def menu_line2(_item):
        with lock:
            return state["line2"]

    intervals_menu = pystray.Menu(intervals_menu_items)

    language_menu = pystray.Menu(
        pystray.MenuItem(
            lambda _item: t(get_lang(cfg), "lang_ru"),
            lambda icon_obj, item: set_language("ru"),
            checked=lang_checked("ru"),
            radio=True,
        ),
        pystray.MenuItem(
            lambda _item: t(get_lang(cfg), "lang_en"),
            lambda icon_obj, item: set_language("en"),
            checked=lang_checked("en"),
            radio=True,
        ),
    )

    about_menu = pystray.Menu(
        pystray.MenuItem(
            lambda _item: t(get_lang(cfg), "menu_version", version=__version__),
            None,
            enabled=False,
        ),
        pystray.MenuItem(
            lambda _item: t(get_lang(cfg), "menu_releases"),
            on_open_releases,
        ),
    )

    menu = pystray.Menu(
        pystray.MenuItem(menu_line1, None, enabled=False),
        pystray.MenuItem(menu_line2, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda _item: t(get_lang(cfg), "menu_intervals"), intervals_menu),
        pystray.MenuItem(lambda _item: t(get_lang(cfg), "menu_choose_map"), on_open_map),
        pystray.MenuItem(lambda _item: t(get_lang(cfg), "menu_refresh"), on_refresh),
        pystray.MenuItem(lambda _item: t(get_lang(cfg), "menu_open_config"), on_open_config),
        pystray.MenuItem(lambda _item: t(get_lang(cfg), "menu_open_log"), on_open_log),
        pystray.MenuItem(lambda _item: t(get_lang(cfg), "menu_language"), language_menu),
        pystray.MenuItem(lambda _item: t(get_lang(cfg), "menu_about"), about_menu),
        pystray.MenuItem(lambda _item: t(get_lang(cfg), "menu_quit"), on_quit),
    )

    icon = pystray.Icon(
        "tray-rain",
        title=t(get_lang(cfg), "weather_title"),
        icon=build_icon(None, False),
        menu=menu,
    )

    def setup(icon_obj):
        icon_obj.visible = True
        threading.Thread(target=refresh_loop, daemon=True).start()

    def run_tray():
        icon.run(setup=setup)

    keepalive_window = webview.create_window("Tray Rain", html="<html></html>", hidden=True)
    webview.start(gui="edgechromium", debug=False, func=run_tray)


if __name__ == "__main__":
    main()
