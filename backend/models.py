from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class Hotspot(BaseModel):
    id: str
    latitude: float
    longitude: float
    brightness: float
    confidence: str # e.g., "l", "n", "h" or numeric string
    acq_date: str
    acq_time: str
    
    # Augmented data
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    ndvi: Optional[float] = None
    
    # Computed risk
    risk_score: Optional[float] = None
    
class RiskCone(BaseModel):
    type: str = "FeatureCollection"
    features: List[Dict[str, Any]]
