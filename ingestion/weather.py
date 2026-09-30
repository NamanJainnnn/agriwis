"""
Weather ingestion — OpenWeather One Call API.
Docs: https://openweathermap.org/api/one-call-3
"""
import os
import requests

OPENWEATHER_KEY = os.environ.get("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/3.0/onecall"


def get_weather(lat: float, lon: float) -> dict:
    """
    Returns current + 7-day forecast summary, or a fallback dict if the
    API key is missing or the call fails. Callers must not crash on a
    missing upstream — this is exactly the kind of gap Block 2 needs to
    handle gracefully.
    """
    if not OPENWEATHER_KEY:
        return _fallback("missing_api_key")

    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_KEY,
        "units": "metric",
        "exclude": "minutely,hourly,alerts",
    }

    try:
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return _fallback(f"request_failed: {e}")

    daily = data.get("daily", [])
    rain_72h_mm = sum(d.get("rain", 0) for d in daily[:3])

    return {
        "status": "ok",
        "current_temp_c": data.get("current", {}).get("temp"),
        "current_humidity_pct": data.get("current", {}).get("humidity"),
        "rain_next_72h_mm": round(rain_72h_mm, 1),
        "forecast_7day": [
            {
                "date": d.get("dt"),
                "temp_max_c": d.get("temp", {}).get("max"),
                "temp_min_c": d.get("temp", {}).get("min"),
                "rain_mm": d.get("rain", 0),
                "conditions": d.get("weather", [{}])[0].get("main"),
            }
            for d in daily[:7]
        ],
    }


def _fallback(reason: str) -> dict:
    return {
        "status": "unavailable",
        "reason": reason,
        "current_temp_c": None,
        "current_humidity_pct": None,
        "rain_next_72h_mm": None,
        "forecast_7day": [],
    }
