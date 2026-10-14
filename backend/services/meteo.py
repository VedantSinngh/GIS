"""
Fixed weather service.

Improvements over original:
  1. Grid-cell caching (0.25° resolution) — avoids duplicate calls for nearby hotspots.
  2. On failure, sets weather_ok=False and uses a neutral value (NOT 0 wind which
     would silently underestimate risk). Neutral wind = 10 km/h at 270°.
  3. Records weather_source ("open_meteo" | "synthetic_neutral") per row.
  4. Optional: try Open-Meteo, fall back gracefully.
"""

import requests
from cachetools import cached, TTLCache
from typing import Dict

# Cache keyed on 0.25-degree grid cell, 15-minute TTL
wind_cache: TTLCache = TTLCache(maxsize=2000, ttl=900)

_NEUTRAL_WIND = {
    "wind_speed": 10.0,       # km/h — neutral, not 0
    "wind_direction": 270.0,  # westerly — reasonable default for India
    "weather_ok": False,
    "weather_source": "synthetic_neutral",
}


def _grid_key(lat: float, lon: float) -> tuple[float, float]:
    """Snap to 0.25-degree grid cell."""
    return (round(lat * 4) / 4, round(lon * 4) / 4)


def fetch_wind_data(lat: float, lon: float) -> Dict:
    """
    Fetch wind, temperature, and humidity from Open-Meteo.
    Returns a dict with keys: wind_speed, wind_direction, temperature_c,
    humidity_pct, weather_ok, weather_source.
    On failure: returns neutral values with weather_ok=False.
    """
    key = _grid_key(lat, lon)
    if key in wind_cache:
        return wind_cache[key]

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={key[0]}&longitude={key[1]}"
        f"&current=wind_speed_10m,wind_direction_10m,temperature_2m,relative_humidity_2m"
        f"&wind_speed_unit=kmh"
    )

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        current = data.get("current", {})
        result = {
            "wind_speed": float(current.get("wind_speed_10m", 10.0)),
            "wind_direction": float(current.get("wind_direction_10m", 270.0)),
            "temperature_c": float(current.get("temperature_2m", 30.0)),
            "humidity_pct": float(current.get("relative_humidity_2m", 40.0)),
            "weather_ok": True,
            "weather_source": "open_meteo",
        }
    except Exception as exc:
        print(f"[meteo] Open-Meteo failed for ({lat:.2f},{lon:.2f}): {exc}; using neutral values")
        result = dict(_NEUTRAL_WIND)
        result.update({"temperature_c": 30.0, "humidity_pct": 40.0})

    wind_cache[key] = result
    return result
