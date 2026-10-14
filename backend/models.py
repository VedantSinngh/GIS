"""
Pydantic models shared between backend routes and (via TypeScript types) the frontend.
Every field here has a matching TypeScript interface in frontend/src/lib/types.ts.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel


# ── Risk breakdown (one component) ───────────────────────────────────────────

class RiskComponent(BaseModel):
    name: str
    normalized: float       # 0-1
    weight: float           # e.g. 0.30
    contribution: float     # normalized * weight, in 0-1
    label: str              # human-readable label


# ── Nearest settlement ────────────────────────────────────────────────────────

class NearSettlement(BaseModel):
    name: str
    state: str
    population: int
    distance_km: float
    bearing_deg: float
    eta_hours: Optional[float] = None   # None if wind toward settlement unknown


# ── Spread ellipse ring ───────────────────────────────────────────────────────

class SpreadRing(BaseModel):
    hours: int
    area_km2: float
    geojson: Dict[str, Any]   # GeoJSON Feature (Polygon)


# ── Smoke plume ───────────────────────────────────────────────────────────────

class SmokePlume(BaseModel):
    aqi_category: str                  # Good / Satisfactory / Moderate / Poor / Very Poor / Severe
    pm25_ug_m3: float
    geojson: Dict[str, Any]            # GeoJSON Feature (Polygon)


# ── Hotspot (core record) ─────────────────────────────────────────────────────

class Hotspot(BaseModel):
    id: str
    latitude: float
    longitude: float

    # VIIRS NRT schema
    brightness: float                  # bright_ti4 alias for backwards compat
    bright_ti4: float
    bright_ti5: Optional[float] = None
    confidence: str                    # "l" | "n" | "h"
    acq_date: str
    acq_time: str
    satellite: Optional[str] = None
    instrument: str = "VIIRS"
    frp: Optional[float] = None
    daynight: Optional[str] = None     # "D" | "N"
    scan: Optional[float] = None
    track: Optional[float] = None

    # Weather enrichment
    wind_speed: Optional[float] = None      # km/h
    wind_direction: Optional[float] = None  # degrees FROM
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    weather_ok: bool = True
    weather_source: str = "synthetic"

    # Vegetation
    ndvi: Optional[float] = None

    # Metadata
    land_cover: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    source: Literal["synthetic", "firms_live"] = "synthetic"
    cluster_id: Optional[str] = None
    persistence_days: Optional[int] = None

    # Risk
    risk_score: Optional[float] = None      # 0-100
    risk_level: Optional[str] = None        # Low / Moderate / High / Extreme
    risk_breakdown: Optional[List[RiskComponent]] = None

    # Optional enrichments (populated only when explicitly requested)
    nearest_settlements: Optional[List[NearSettlement]] = None
    spread_rings: Optional[List[SpreadRing]] = None
    smoke_plume: Optional[SmokePlume] = None


# ── Hotspot list response ─────────────────────────────────────────────────────

class HotspotsResponse(BaseModel):
    data_source: str
    generated_at: str
    total: int
    hotspots: List[Hotspot]


# ── Alert ─────────────────────────────────────────────────────────────────────

class Alert(BaseModel):
    id: str
    hotspot_id: str
    severity: Literal["Info", "Warning", "Critical", "Extreme"]
    message: str
    settlement_name: Optional[str] = None
    distance_km: Optional[float] = None
    risk_score: float
    acq_date: str


# ── Alerts response ───────────────────────────────────────────────────────────

class AlertsResponse(BaseModel):
    total: int
    alerts: List[Alert]


# ── Analytics ─────────────────────────────────────────────────────────────────

class DailyCount(BaseModel):
    date: str
    count: int

class RiskLevelCount(BaseModel):
    level: str
    count: int

class StateCount(BaseModel):
    state: str
    count: int

class TopHotspot(BaseModel):
    id: str
    latitude: float
    longitude: float
    risk_score: float
    state: Optional[str]
    acq_date: str

class AnalyticsResponse(BaseModel):
    fires_per_day: List[DailyCount]
    risk_distribution: List[RiskLevelCount]
    state_counts: List[StateCount]
    top_hotspots: List[TopHotspot]


# ── Spread response ────────────────────────────────────────────────────────────

class SpreadResponse(BaseModel):
    hotspot_id: str
    wind_speed: float
    wind_direction: float
    rings: List[SpreadRing]


# ── Exposure response ─────────────────────────────────────────────────────────

class ExposureResponse(BaseModel):
    hotspot_id: str
    radius_km: float
    total_population_at_risk: int
    settlements: List[NearSettlement]


# ── Legacy cone (kept for backwards compat) ───────────────────────────────────

class RiskCone(BaseModel):
    type: str = "FeatureCollection"
    features: List[Dict[str, Any]]
