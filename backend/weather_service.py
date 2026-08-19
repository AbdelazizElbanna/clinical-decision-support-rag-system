"""
Fetches 100% REAL LIVE weather + air quality from MET Norway / Open-Meteo.
Resolves governorate name -> lat/lon from cities.json.
"""

import json
import asyncio
import httpx
import math
import datetime
from typing import Optional
from config import CITIES_JSON_PATH

with open(CITIES_JSON_PATH, encoding="utf-8") as f:
    _CITIES = json.load(f)


def resolve_governorate(governorate_en: str) -> Optional[dict]:
    """Find city record by name, capital, or alias (case-insensitive)."""
    q = governorate_en.strip().lower()
    for gov in _CITIES:
        if gov.get("governorate_en", "").lower() == q:
            return gov
        if gov.get("capital_en", "").lower() == q:
            return gov
        if gov.get("governorate_ar", "").strip() == governorate_en.strip():
            return gov
        if gov.get("capital_ar", "").strip() == governorate_en.strip():
            return gov
        aliases = [a.lower() for a in gov.get("aliases", [])]
        if q in aliases:
            return gov
    return None
    return None


async def fetch_weather(lat: float, lon: float, gov_en: str = "Cairo") -> dict:
    """Fetch weather + air quality for coordinates from Open-Meteo API."""
    try:
        # Increased timeout to 10.0 seconds to prevent 500 errors or timeout issues
        async with httpx.AsyncClient(timeout=10.0) as client:
            w_params = {
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,uv_index,wind_speed_10m",
                "timezone": "auto"
            }
            aq_params = {
                "latitude": lat, "longitude": lon,
                "current": "pm2_5,dust,european_aqi",
                "timezone": "auto"
            }
            w_res, aq_res = await asyncio.gather(
                client.get("https://api.open-meteo.com/v1/forecast", params=w_params),
                client.get("https://air-quality-api.open-meteo.com/v1/air-quality", params=aq_params)
            )

        if w_res.status_code != 200 or aq_res.status_code != 200:
            print(f"Open-Meteo API error: weather {w_res.status_code}, aq {aq_res.status_code}")
            return {}

        w = w_res.json().get("current", {})
        aq = aq_res.json().get("current", {})

        temp = w.get("temperature_2m")
        humidity = w.get("relative_humidity_2m")
        uv = w.get("uv_index")
        dust = aq.get("dust")
        pm25 = aq.get("pm2_5")
        
        # If the API returns None for temperature, it's a failure
        if temp is None:
            return {}

        return {
            "temperature_c": temp,
            "apparent_temperature_c": w.get("apparent_temperature"),
            "humidity_percent": humidity,
            "uv_index": uv,
            "wind_speed_kmh": w.get("wind_speed_10m"),
            "pm2_5": pm25,
            "dust": dust,
            "european_aqi": aq.get("european_aqi"),
            "skin_alerts": _skin_risk(temp, humidity, uv, pm25, dust)
        }
    except Exception as e:
        print(f"Weather API error: {e}")
        return {}


def _skin_risk(temp, humidity, uv, pm25, dust) -> list:
    alerts = []
    if humidity is not None and humidity < 35:
        alerts.append("Low humidity (<35%): High risk of skin barrier dryness and eczema flare.")
    if temp is not None and temp > 35 and humidity is not None and humidity > 60:
        alerts.append("High heat + humidity: Sweating may trigger urticaria and itching.")
    if uv is not None and uv >= 6:
        alerts.append(f"UV Index {uv} (High): Photosensitivity risk. Use mineral sunscreen SPF 50+.")
    if dust is not None and dust > 50:
        alerts.append(f"Elevated dust ({dust} µg/m3): Rinse skin after outdoor exposure.")
    if pm25 is not None and pm25 > 35:
        alerts.append(f"PM2.5 elevated ({pm25} µg/m3): May worsen atopic skin inflammation.")
    if not alerts:
        alerts.append("Environmental conditions are within acceptable range for skin conditions today.")
    return alerts
