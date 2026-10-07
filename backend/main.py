from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import hashlib

from config import DEFAULT_BBOX
from models import Hotspot, RiskCone
from services.firms import fetch_firms_hotspots
from services.meteo import fetch_wind_data
from services.risk import calculate_risk_score, generate_risk_cone

app = FastAPI(title="Wildfire Risk Monitor API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/hotspots", response_model=List[Hotspot])
def get_hotspots(bbox: str = Query(DEFAULT_BBOX, description="Bounding box in format W,S,E,N")):
    """
    Fetch active FIRMS hotspots, enrich with wind and NDVI, and compute risk score.
    """
    try:
        firms_data = fetch_firms_hotspots(bbox)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"FIRMS data temporarily unavailable: {str(e)}")
        
    hotspots = []
    
    for pt in firms_data:
        lat = pt["latitude"]
        lon = pt["longitude"]
        
        # Generate a stable ID for the hotspot
        id_str = f"{lat}_{lon}_{pt['acq_date']}_{pt['acq_time']}"
        pt_id = hashlib.md5(id_str.encode()).hexdigest()
        
        # Fetch wind data
        wind = fetch_wind_data(lat, lon)
        wind_speed = wind["wind_speed"]
        wind_direction = wind["wind_direction"]
        
        # NDVI lookup (skipped for first pass, will be None)
        ndvi = None 
        
        # Calculate risk score
        risk_score = calculate_risk_score(
            brightness=pt["brightness"],
            confidence=pt["confidence"],
            wind_speed=wind_speed,
            ndvi=ndvi
        )
        
        hotspot = Hotspot(
            id=pt_id,
            latitude=lat,
            longitude=lon,
            brightness=pt["brightness"],
            confidence=pt["confidence"],
            acq_date=pt["acq_date"],
            acq_time=pt["acq_time"],
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            ndvi=ndvi,
            risk_score=risk_score
        )
        hotspots.append(hotspot)
        
    return hotspots

@app.get("/risk-cone/{hotspot_id}")
def get_risk_cone(
    hotspot_id: str, 
    lat: float = Query(..., description="Latitude of hotspot"), 
    lon: float = Query(..., description="Longitude of hotspot"),
    wind_speed: float = Query(..., description="Wind speed in km/h"),
    wind_direction: float = Query(..., description="Wind direction in degrees")
):
    """
    Returns a GeoJSON Polygon representing a projected spread direction based on wind.
    """
    feature = generate_risk_cone(lat, lon, wind_speed, wind_direction)
    
    return {
        "type": "FeatureCollection",
        "features": [feature]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
