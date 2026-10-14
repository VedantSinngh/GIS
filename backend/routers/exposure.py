"""
/exposure/{hotspot_id} and /alerts routers.
"""

from __future__ import annotations

import hashlib
from fastapi import APIRouter, Query
from typing import List

import config
from models import ExposureResponse, AlertsResponse, Alert
from services.risk import find_nearby_settlements, generate_smoke_plume
from synthetic.settlements import load_settlements
from synthetic.generator import get_cached_hotspots

router = APIRouter()


@router.get("/exposure/{hotspot_id}", response_model=ExposureResponse)
def get_exposure(
    hotspot_id: str,
    lat: float = Query(...),
    lon: float = Query(...),
    wind_speed: float = Query(10.0),
    wind_direction: float = Query(270.0),
    radius_km: float = Query(config.EXPOSURE_RADIUS_KM),
):
    """
    Returns settlements within radius_km of the hotspot, population at risk,
    and ETA for settlements in the fire's path.
    """
    settlements = load_settlements()
    nearby = find_nearby_settlements(lat, lon, wind_speed, wind_direction, settlements, radius_km)
    total_pop = sum(s.population for s in nearby)
    return ExposureResponse(
        hotspot_id=hotspot_id,
        radius_km=radius_km,
        total_population_at_risk=total_pop,
        settlements=nearby,
    )


@router.get("/alerts", response_model=AlertsResponse)
def get_alerts(min_risk: float = Query(50.0)):
    """
    Auto-generated alerts sorted by severity. Considers any hotspot with
    risk >= min_risk that has settlements within 10 km.
    """
    from routers.hotspots import _build_hotspot_from_row

    settlements = load_settlements()
    df = get_cached_hotspots(days=config.SYNTHETIC_DAYS, seed=config.SYNTHETIC_SEED)
    rows = df.to_dict(orient="records")

    alerts: List[Alert] = []

    for row in rows:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        wind_speed = float(row.get("wind_speed_kmh", 10.0))
        wind_dir   = float(row.get("wind_dir_deg", 270.0))

        hotspot = _build_hotspot_from_row(row, settlements)
        risk = hotspot.risk_score or 0

        if risk < min_risk:
            continue

        nearby = find_nearby_settlements(lat, lon, wind_speed, wind_dir, settlements, 10.0)
        if not nearby:
            continue

        closest = nearby[0]

        if risk >= 75:
            severity = "Extreme"
        elif risk >= 60:
            severity = "Critical"
        elif risk >= 45:
            severity = "Warning"
        else:
            severity = "Info"

        eta_str = f", ETA {closest.eta_hours:.1f}h" if closest.eta_hours else ""
        msg = (
            f"{severity} risk fire ({risk:.0f}/100) {closest.distance_km:.1f} km from "
            f"{closest.name}{eta_str}. Wind: {wind_speed:.0f} km/h."
        )

        alert_id = hashlib.md5(f"{hotspot.id}_{closest.name}".encode()).hexdigest()[:12]
        alerts.append(Alert(
            id=alert_id,
            hotspot_id=hotspot.id,
            severity=severity,
            message=msg,
            settlement_name=closest.name,
            distance_km=closest.distance_km,
            risk_score=risk,
            acq_date=hotspot.acq_date,
        ))

    alerts.sort(key=lambda a: a.risk_score, reverse=True)
    return AlertsResponse(total=len(alerts), alerts=alerts[:100])
