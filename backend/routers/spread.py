"""
/spread/{hotspot_id} router
GET /spread/{id}?lat=&lon=&wind_speed=&wind_direction=&hours=1,3,6,12
Returns SpreadResponse with elliptical rings for each time horizon.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from typing import List

from models import SpreadResponse, SpreadRing
from services.risk import generate_spread_ellipse

router = APIRouter()


@router.get("/spread/{hotspot_id}", response_model=SpreadResponse)
def get_spread(
    hotspot_id: str,
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    wind_speed: float = Query(..., description="Wind speed km/h"),
    wind_direction: float = Query(..., description="Wind direction degrees FROM"),
    hours: str = Query("1,3,6,12", description="Comma-separated projection hours"),
):
    """
    Returns fire-spread ellipses (Anderson 1983 / FARSITE-style) for each
    requested time horizon.

    LBR = 1 + 0.125 × U  (U = wind speed km/h)
    ROS = ROS_BASE × (1 + 0.04 × U) km/h
    semi-major a = ROS × hours, semi-minor b = a / LBR
    """
    hour_list: List[int] = []
    for h in hours.split(","):
        try:
            hour_list.append(int(h.strip()))
        except ValueError:
            pass
    if not hour_list:
        hour_list = [1, 3, 6, 12]

    rings: List[SpreadRing] = [
        generate_spread_ellipse(lat, lon, wind_speed, wind_direction, h)
        for h in sorted(set(hour_list))
    ]

    return SpreadResponse(
        hotspot_id=hotspot_id,
        wind_speed=wind_speed,
        wind_direction=wind_direction,
        rings=rings,
    )
