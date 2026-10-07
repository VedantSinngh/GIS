import requests
from cachetools import cached, TTLCache

# Cache wind data for 15 minutes (900 seconds)
wind_cache = TTLCache(maxsize=1000, ttl=900)

@cached(wind_cache)
def fetch_wind_data(lat: float, lon: float) -> dict:
    """
    Fetch wind speed and direction from Open-Meteo.
    Docs: https://open-meteo.com/en/docs
    """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=wind_speed_10m,wind_direction_10m&wind_speed_unit=kmh"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        current = data.get("current", {})
        return {
            "wind_speed": current.get("wind_speed_10m", 0.0),
            "wind_direction": current.get("wind_direction_10m", 0.0)
        }
    except Exception as e:
        print(f"Error fetching wind data for {lat},{lon}: {e}")
        return {
            "wind_speed": 0.0,
            "wind_direction": 0.0
        }
