# Tray Rain (Windows)
I'm **not a Python developer**, so this is a purely **amateur / hobby project**.  
The code was written for personal use only and has a lot of room for improvements and optimizations.

Small Windows tray app that shows current temperature and whether rain is expected today.
Now includes a map-based location picker from the tray menu.

## Setup

1. Create a virtual environment (optional)
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run

```powershell
python app.py
```

To hide the console window:

```powershell
pythonw app.py
```


## Map Location Picker

Use the tray menu item `Выбрать локацию на карте`, click on the map, then press **Сохранить координаты**.
The app writes the selected latitude/longitude into `config.json`.

## Configure

Edit `config.json`:

- `latitude` / `longitude`: location
- `timezone`: IANA timezone, for example `Europe/Moscow`
- `refresh_minutes`: update interval
- `rain_threshold_mm`: rain if hourly precipitation >= this value


## Build (Windows)

1. Install build dependency:

```powershell
pip install pyinstaller
```

2. Build a no-console executable (includes `config.json` and `map.html`):

```powershell
pyinstaller -y --noconsole --name tray-rain --add-data "config.json;." --add-data "map.html;." app.py
```

Output will be in `dist/tray-rain/`.

## Notes

The app uses Open-Meteo (no API key) and keeps everything local.
