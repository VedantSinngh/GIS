import requests
import csv
from io import StringIO
from cachetools import cached, TTLCache
from config import FIRMS_MAP_KEY

# Cache for 3 hours (10800 seconds) since FIRMS updates roughly every 3 hours
firms_cache = TTLCache(maxsize=10, ttl=10800)

@cached(firms_cache)
def fetch_firms_hotspots(bbox: str) -> list:
    """
    Fetch active fire hotspots from NASA FIRMS Area API.
    Docs: https://firms.modaps.eosdis.nasa.gov/api/area/
    Using MODIS (MOD14) or VIIRS (SUOMI NPP). We'll use VIIRS (SNPP) for better resolution.
    Format: https://firms.modaps.eosdis.nasa.gov/api/area/csv/[MAP_KEY]/VIIRS_SNPP_NRT/[BBOX]/1
    The '1' at the end is for 1 day (last 24 hours).
    """
    if FIRMS_MAP_KEY == "DEMO_KEY" or not FIRMS_MAP_KEY:
        # If no key, we might want to return mock data for testing, but let's try the request, it will fail.
        # Let's mock a couple of points for Uttarakhand if DEMO_KEY is used.
        if FIRMS_MAP_KEY == "DEMO_KEY":
            print("WARNING: Using mock FIRMS data because FIRMS_MAP_KEY is not set.")
            return [
                {
                    "latitude": 30.3,
                    "longitude": 78.0,
                    "brightness": 330.5,
                    "confidence": "n",
                    "acq_date": "2023-10-01",
                    "acq_time": "1200"
                },
                {
                    "latitude": 29.5,
                    "longitude": 79.5,
                    "brightness": 345.1,
                    "confidence": "h",
                    "acq_date": "2023-10-01",
                    "acq_time": "1430"
                },
                {
                    "latitude": 30.1,
                    "longitude": 79.1,
                    "brightness": 310.2,
                    "confidence": "l",
                    "acq_date": "2023-10-01",
                    "acq_time": "1530"
                }
            ]

    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_MAP_KEY}/VIIRS_SNPP_NRT/{bbox}/1"
    
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    
    # Parse CSV
    csv_data = StringIO(response.text)
    reader = csv.DictReader(csv_data)
    
    hotspots = []
    for row in reader:
        # Expected columns: latitude, longitude, brightness, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_t31, frp, daynight
        hotspots.append({
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "brightness": float(row["brightness"]),
            "confidence": row["confidence"], # n=nominal, l=low, h=high
            "acq_date": row["acq_date"],
            "acq_time": row["acq_time"]
        })
        
    return hotspots
