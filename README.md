# Tray Rain (Windows)
I'm **not a Python developer**, so this is a purely **amateur / hobby project**.  
The code was written for personal use only and has a lot of room for improvements and optimizations.

Small Windows tray app that shows current temperature and whether rain is expected today.

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

## Configure

Edit `config.json`:

- `latitude` / `longitude`: location
- `timezone`: IANA timezone, for example `Europe/Moscow`
- `refresh_minutes`: update interval
- `rain_threshold_mm`: rain if hourly precipitation >= this value

## Notes

The app uses Open-Meteo (no API key) and keeps everything local.
