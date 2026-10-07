import math

def calculate_risk_score(brightness: float, confidence: str, wind_speed: float, ndvi: float = None) -> float:
    """
    Heuristic decision-support estimate for wildfire spread risk.
    NOT a certified fire-behavior model.
    
    Weights:
    - Fire brightness & confidence: 40%
    - Wind speed: 40%
    - NDVI (dryness): 20%
    
    Brightness is typically 295K - 400K.
    Wind speed in km/h, typically 0 - 100.
    NDVI typically -1 to 1. Lower means drier vegetation.
    """
    
    # 1. Normalize Brightness & Confidence (0-100)
    # VIIRS brightness typically ranges from 295K to 380K+
    b_norm = min(max((brightness - 295) / (380 - 295) * 100, 0), 100)
    
    conf_multiplier = 1.0
    if confidence == "l":
        conf_multiplier = 0.5
    elif confidence == "h":
        conf_multiplier = 1.2
        
    fire_factor = min(b_norm * conf_multiplier, 100)
    
    # 2. Normalize Wind Speed (0-100)
    # Assume 50 km/h is highly dangerous
    wind_factor = min((wind_speed / 50.0) * 100, 100)
    
    # 3. Normalize NDVI (0-100)
    # Lower NDVI (e.g., 0.1 to 0.3) means dry vegetation -> higher risk
    # If NDVI is not available, assume a neutral risk contribution (e.g. 50/100)
    if ndvi is None:
        ndvi_factor = 50.0
    else:
        # Invert NDVI: dry (low) = high risk, wet (high) = low risk
        if ndvi < 0.1:
            ndvi_factor = 80.0
        elif ndvi > 0.6:
            ndvi_factor = 20.0
        else:
            # Linear from 0.1 -> 80 to 0.6 -> 20
            ndvi_factor = 80.0 - ((ndvi - 0.1) / 0.5) * 60.0
            
    # Combine with weights
    risk_score = (fire_factor * 0.4) + (wind_factor * 0.4) + (ndvi_factor * 0.2)
    
    return min(max(round(risk_score, 1), 0), 100)

def generate_risk_cone(lat: float, lon: float, wind_speed: float, wind_direction: float) -> dict:
    """
    Generates a GeoJSON polygon representing a projected spread cone.
    Length proportional to wind speed.
    Direction based on wind direction (meteorological: direction wind is coming FROM).
    """
    # Spread direction is opposite of wind origin
    spread_deg = (wind_direction + 180) % 360
    spread_rad = math.radians(spread_deg)
    
    # Base distance (e.g. 0.01 deg lat/lon ~ 1km)
    # Let's say 10 km/h wind creates a cone of 0.02 deg length
    cone_length = max(0.01, (wind_speed / 10.0) * 0.02)
    
    # Cone width angle (e.g. 30 degrees spread on each side)
    spread_angle_rad = math.radians(30)
    
    left_rad = spread_rad - spread_angle_rad
    right_rad = spread_rad + spread_angle_rad
    
    # Calculate cone points
    p1 = [lon, lat] # Tip of the cone
    
    p2_lon = lon + cone_length * math.sin(left_rad)
    p2_lat = lat + cone_length * math.cos(left_rad)
    
    p3_lon = lon + cone_length * math.sin(right_rad)
    p3_lat = lat + cone_length * math.cos(right_rad)
    
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                p1,
                [p2_lon, p2_lat],
                [p3_lon, p3_lat],
                p1
            ]]
        },
        "properties": {
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "spread_direction": spread_deg
        }
    }
    
    return feature
