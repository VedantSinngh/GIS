"""
/hotspots router
GET /hotspots?bbox=&start=&end=&confidence=&state=&land_cover=&daynight=&min_risk=
Returns HotspotsResponse with data_source, generated_at, total, and hotspot list.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

import config
from models import Hotspot, HotspotsResponse, RiskComponent
from services.meteo import fetch_wind_data
from services.risk import calculate_risk_score
from synthetic.generator import get_cached_hotspots
from synthetic.settlements import load_settlements

router = APIRouter()


def _build_hotspot_from_row(row: dict, settlements: list) -> Hotspot:
    """Convert a generator-row dict into a validated Hotspot with risk scores."""
    from services.risk import find_nearby_settlements

    wind_speed = float(row.get("wind_speed_kmh", 10.0))
    wind_dir   = float(row.get("wind_dir_deg", 270.0))
    temp_c     = row.get("temperature_c")
    humidity   = row.get("humidity_pct")
    ndvi       = row.get("ndvi")
    frp        = row.get("frp")
    persistence= row.get("persistence_days")
    lat        = float(row["latitude"])
    lon        = float(row["longitude"])

    # Exposure (fast — only use narrow radius for per-hotspot lookup)
    nearby = find_nearby_settlements(
        lat, lon, wind_speed, wind_dir, settlements,
        radius_km=config.EXPOSURE_RADIUS_KM
    )
    pop_at_risk = sum(s.population for s in nearby)

    risk_score, risk_level, breakdown = calculate_risk_score(
        brightness=float(row["brightness"]),
        confidence=row.get("confidence", "n"),
        wind_speed=wind_speed,
        ndvi=ndvi,
        frp=frp,
        humidity_pct=humidity,
        temperature_c=temp_c,
        population_within_radius=pop_at_risk,
        persistence_days=persistence,
    )

    return Hotspot(
        id=row.get("id") or hashlib.md5(f"{lat}_{lon}_{row.get('acq_date','')}".encode()).hexdigest(),
        latitude=lat,
        longitude=lon,
        brightness=float(row["brightness"]),
        bright_ti4=float(row.get("bright_ti4", row["brightness"])),
        bright_ti5=row.get("bright_ti5"),
        confidence=row.get("confidence", "n"),
        acq_date=row.get("acq_date", date.today().isoformat()),
        acq_time=row.get("acq_time", "0800"),
        satellite=row.get("satellite"),
        instrument=row.get("instrument", "VIIRS"),
        frp=frp,
        daynight=row.get("daynight"),
        scan=row.get("scan"),
        track=row.get("track"),
        wind_speed=wind_speed,
        wind_direction=wind_dir,
        temperature_c=temp_c,
        humidity_pct=humidity,
        weather_ok=row.get("weather_ok", True),
        weather_source=row.get("weather_source", "synthetic"),
        ndvi=ndvi,
        land_cover=row.get("land_cover"),
        state=row.get("state"),
        region=row.get("region"),
        source=row.get("source", "synthetic"),
        cluster_id=row.get("cluster_id"),
        persistence_days=persistence,
        risk_score=risk_score,
        risk_level=risk_level,
        risk_breakdown=breakdown,
    )


def _fetch_live_hotspots(bbox: str, start: Optional[str], end: Optional[str]) -> list[dict]:
    """Try NASA FIRMS live. Raises on failure."""
    from services.firms import fetch_firms_hotspots
    rows = fetch_firms_hotspots(bbox)
    # Date filter (live always returns last 1 day)
    return rows


@router.get("/hotspots", response_model=HotspotsResponse)
def get_hotspots(
    bbox: str = Query(config.DEFAULT_BBOX, description="W,S,E,N"),
    start: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    end:   Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    confidence: Optional[str] = Query(None, description="l,n,h (comma-separated)"),
    state: Optional[str] = Query(None, description="State name filter"),
    land_cover: Optional[str] = Query(None, description="Land cover type"),
    daynight: Optional[str] = Query(None, description="D or N"),
    min_risk: float = Query(0, description="Minimum risk score 0-100"),
):
    source_mode = config.DATA_SOURCE
    settlements = load_settlements()

    raw_rows: list[dict] = []

    # ── Resolve data source ────────────────────────────────────────────────
    if source_mode == "live":
        try:
            raw_rows = _fetch_live_hotspots(bbox, start, end)
            actual_source = "firms_live"
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Live FIRMS unavailable: {exc}")

    elif source_mode == "hybrid":
        try:
            raw_rows = _fetch_live_hotspots(bbox, start, end)
            actual_source = "firms_live"
        except Exception:
            df = get_cached_hotspots(days=config.SYNTHETIC_DAYS, seed=config.SYNTHETIC_SEED)
            raw_rows = df.to_dict(orient="records")
            actual_source = "synthetic"
    else:
        # synthetic (default)
        df = get_cached_hotspots(days=config.SYNTHETIC_DAYS, seed=config.SYNTHETIC_SEED)
        raw_rows = df.to_dict(orient="records")
        actual_source = "synthetic"

    # ── Bbox filter ────────────────────────────────────────────────────────
    try:
        w, s, e, n = map(float, bbox.split(","))
    except Exception:
        w, s, e, n = -180, -90, 180, 90

    rows = [
        r for r in raw_rows
        if w <= float(r["longitude"]) <= e and s <= float(r["latitude"]) <= n
    ]

    # ── Date filter ────────────────────────────────────────────────────────
    if start:
        rows = [r for r in rows if r.get("acq_date", "9999") >= start]
    if end:
        rows = [r for r in rows if r.get("acq_date", "0000") <= end]

    # ── Attribute filters ──────────────────────────────────────────────────
    if confidence:
        allowed = {c.strip().lower() for c in confidence.split(",")}
        rows = [r for r in rows if r.get("confidence", "n").lower() in allowed]
    if state:
        rows = [r for r in rows if r.get("state", "").lower() == state.lower()]
    if land_cover:
        rows = [r for r in rows if r.get("land_cover", "").lower() == land_cover.lower()]
    if daynight:
        rows = [r for r in rows if r.get("daynight", "").upper() == daynight.upper()]

    # ── Build hotspots ─────────────────────────────────────────────────────
    hotspots = [_build_hotspot_from_row(r, settlements) for r in rows]

    # ── Risk filter ────────────────────────────────────────────────────────
    if min_risk > 0:
        hotspots = [h for h in hotspots if (h.risk_score or 0) >= min_risk]

    return HotspotsResponse(
        data_source=actual_source,
        generated_at=datetime.utcnow().isoformat() + "Z",
        total=len(hotspots),
        hotspots=hotspots,
    )
