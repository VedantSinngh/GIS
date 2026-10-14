"""
5-Factor Risk Model — heuristic decision-support tool.
NOT a certified fire-behaviour model.

Score = Σ(weight_i × factor_i), all factors in [0,1], score in [0,100].

Factors and weights (configurable in config.py):
  1. Intensity   (30%): brightness temperature + FRP + confidence multiplier
  2. Wind        (25%): wind speed (km/h)
  3. Fuel Dryness(25%): NDVI + humidity + temperature → simplified FWI-style index
  4. Exposure    (10%): population within EXPOSURE_RADIUS_KM
  5. Persistence (10%): number of days the cluster has been burning

Spread Ellipse:
  Anderson 1983 / FARSITE-style length-to-breadth ratio:
    LBR = 1 + 0.125 × U   (U = wind speed km/h)
  Ellipse semi-major axis a (km) = ROS × hours, semi-minor b = a / LBR
  Converted to GeoJSON Polygon (N=72 points).

Degrees-to-km conversion (corrected from original raw-degree bug):
  Δlat_deg = km / 111.32
  Δlon_deg = km / (111.32 × cos(lat_rad))

Smoke Plume:
  Simplified 2D Gaussian PM2.5 estimate downwind.
  PM2.5 ∝ FRP × exp(-r²/(2σ²)) where σ grows with downwind distance.
"""

from __future__ import annotations

import math
from typing import List, Optional, Dict, Any

import config
from models import RiskComponent, SpreadRing, SmokePlume, NearSettlement


# ── Constants ─────────────────────────────────────────────────────────────────
KM_PER_DEG_LAT = 111.32


def _km_to_deg_lon(km: float, lat: float) -> float:
    return km / (KM_PER_DEG_LAT * math.cos(math.radians(lat)))


def _km_to_deg_lat(km: float) -> float:
    return km / KM_PER_DEG_LAT


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δλ = math.radians(lon2 - lon1)
    x = math.sin(Δλ) * math.cos(φ2)
    y = math.cos(φ1) * math.sin(φ2) - math.sin(φ1) * math.cos(φ2) * math.cos(Δλ)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


# ── Factor helpers ────────────────────────────────────────────────────────────

def _intensity_factor(brightness: float, frp: Optional[float], confidence: str) -> float:
    """
    Normalized intensity in [0,1].
    brightness: VIIRS bright_ti4 (K), typical range 300-367.
    frp: Fire Radiative Power (MW), 0.5-150, log-scaled.
    """
    b_norm = min(max((brightness - 300) / 67.0, 0.0), 1.0)

    if frp is not None and frp > 0:
        frp_norm = min(math.log1p(frp) / math.log1p(150), 1.0)
    else:
        frp_norm = b_norm  # fallback

    conf_mult = {"l": 0.7, "n": 1.0, "h": 1.2}.get(confidence.lower(), 1.0)
    raw = (b_norm * 0.5 + frp_norm * 0.5) * conf_mult
    return min(max(raw, 0.0), 1.0)


def _wind_factor(wind_speed_kmh: float) -> float:
    """Normalized wind in [0,1]. 50 km/h = 1.0."""
    return min(wind_speed_kmh / 50.0, 1.0)


def _fuel_dryness_factor(
    ndvi: Optional[float],
    humidity_pct: Optional[float],
    temperature_c: Optional[float],
) -> float:
    """
    Simplified Fuel Dryness in [0,1].
    Inspired by McArthur Fire Danger Rating / Keetch-Byram Drought Index concepts.

    NDVI component: low NDVI (dry/sparse vegetation) → high risk.
      ndvi_risk = 1 - clip(ndvi, 0, 1)   (if None → neutral 0.5)

    Humidity component: lower humidity → higher risk.
      hum_risk = 1 - humidity_pct / 100  (if None → neutral 0.4)

    Temperature component: higher temp → higher risk.
      temp_risk = clip((temp_c - 20) / 30, 0, 1)  (if None → neutral 0.5)

    Combined: 0.5*ndvi_risk + 0.3*hum_risk + 0.2*temp_risk
    """
    ndvi_risk = (1.0 - min(max(ndvi, 0.0), 1.0)) if ndvi is not None else 0.5
    hum_risk = (1.0 - (humidity_pct / 100.0)) if humidity_pct is not None else 0.4
    temp_risk = min(max((temperature_c - 20) / 30.0, 0.0), 1.0) if temperature_c is not None else 0.5
    return 0.5 * ndvi_risk + 0.3 * hum_risk + 0.2 * temp_risk


def _exposure_factor(population_within_radius: int, max_pop: int = 500_000) -> float:
    """Normalized population exposure in [0,1] using log scale."""
    if population_within_radius <= 0:
        return 0.0
    return min(math.log1p(population_within_radius) / math.log1p(max_pop), 1.0)


def _persistence_factor(days: Optional[int]) -> float:
    """Older fires that keep burning are more dangerous. Cap at 6 days."""
    if days is None:
        return 0.3
    return min(days / 6.0, 1.0)


# ── Main risk scorer ──────────────────────────────────────────────────────────

def calculate_risk_score(
    brightness: float,
    confidence: str,
    wind_speed: float,
    ndvi: Optional[float] = None,
    frp: Optional[float] = None,
    humidity_pct: Optional[float] = None,
    temperature_c: Optional[float] = None,
    population_within_radius: int = 0,
    persistence_days: Optional[int] = None,
) -> tuple[float, str, List[RiskComponent]]:
    """
    Returns (risk_score_0_to_100, risk_level, breakdown_list).

    risk_level: "Low" | "Moderate" | "High" | "Extreme"
    breakdown: list of RiskComponent with per-factor contribution details.
    """
    f_intensity   = _intensity_factor(brightness, frp, confidence)
    f_wind        = _wind_factor(wind_speed)
    f_fuel        = _fuel_dryness_factor(ndvi, humidity_pct, temperature_c)
    f_exposure    = _exposure_factor(population_within_radius)
    f_persistence = _persistence_factor(persistence_days)

    w = [
        config.RISK_WEIGHT_INTENSITY,
        config.RISK_WEIGHT_WIND,
        config.RISK_WEIGHT_FUEL,
        config.RISK_WEIGHT_EXPOSURE,
        config.RISK_WEIGHT_PERSISTENCE,
    ]
    f = [f_intensity, f_wind, f_fuel, f_exposure, f_persistence]

    score_raw = sum(wi * fi for wi, fi in zip(w, f))
    score = round(min(max(score_raw * 100, 0), 100), 1)

    if score >= 75:
        level = "Extreme"
    elif score >= 50:
        level = "High"
    elif score >= 25:
        level = "Moderate"
    else:
        level = "Low"

    breakdown = [
        RiskComponent(name="Intensity",   normalized=round(f_intensity, 3),   weight=w[0], contribution=round(w[0]*f_intensity,4),   label="Fire brightness + FRP + confidence"),
        RiskComponent(name="Wind",        normalized=round(f_wind, 3),        weight=w[1], contribution=round(w[1]*f_wind,4),        label="Wind speed (km/h)"),
        RiskComponent(name="Fuel Dryness",normalized=round(f_fuel, 3),        weight=w[2], contribution=round(w[2]*f_fuel,4),        label="NDVI + humidity + temperature"),
        RiskComponent(name="Exposure",    normalized=round(f_exposure, 3),    weight=w[3], contribution=round(w[3]*f_exposure,4),    label="Population within 10 km"),
        RiskComponent(name="Persistence", normalized=round(f_persistence, 3), weight=w[4], contribution=round(w[4]*f_persistence,4), label="Days cluster has been burning"),
    ]

    return score, level, breakdown


# ── Spread ellipse ─────────────────────────────────────────────────────────────

def generate_spread_ellipse(
    lat: float,
    lon: float,
    wind_speed: float,
    wind_direction: float,
    hours: int = 6,
) -> SpreadRing:
    """
    Wind-driven ellipse using Anderson (1983) length-to-breadth ratio.

    LBR = 1 + 0.125 × U   (U in km/h; at 0 wind LBR=1 → circle)
    ROS (rate of spread, km/h) = SPREAD_ROS_BASE_KMH × (1 + 0.04 × U)
    semi-major axis a = ROS × hours
    semi-minor axis  b = a / LBR

    Spread direction = (wind_direction + 180) % 360 (downwind).
    Returns a SpreadRing with GeoJSON Polygon in lat/lon degrees.
    """
    U = max(wind_speed, 0.0)
    lbr = 1.0 + 0.125 * U
    ros = config.SPREAD_ROS_BASE_KMH * (1.0 + 0.04 * U)
    a_km = ros * hours          # semi-major (downwind), km
    b_km = a_km / lbr           # semi-minor (crosswind), km
    area_km2 = math.pi * a_km * b_km

    spread_rad = math.radians((wind_direction + 180) % 360)

    # Build ellipse polygon (72 points)
    N = 72
    coords: List[List[float]] = []
    for i in range(N):
        θ = 2 * math.pi * i / N
        # Ellipse in local Cartesian (downwind = +x, crosswind = +y)
        x_km = a_km * math.cos(θ)
        y_km = b_km * math.sin(θ)
        # Rotate into geographic direction
        bearing = spread_rad
        e_km = x_km * math.sin(bearing) + y_km * math.cos(bearing)
        n_km = x_km * math.cos(bearing) - y_km * math.sin(bearing)
        pt_lat = lat + _km_to_deg_lat(n_km)
        pt_lon = lon + _km_to_deg_lon(e_km, lat)
        coords.append([round(pt_lon, 5), round(pt_lat, 5)])
    coords.append(coords[0])  # close ring

    geojson: Dict[str, Any] = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [coords]},
        "properties": {
            "hours": hours,
            "wind_speed_kmh": wind_speed,
            "ros_kmh": round(ros, 3),
            "lbr": round(lbr, 3),
            "a_km": round(a_km, 3),
            "b_km": round(b_km, 3),
            "area_km2": round(area_km2, 2),
        },
    }
    return SpreadRing(hours=hours, area_km2=round(area_km2, 2), geojson=geojson)


def generate_risk_cone(lat: float, lon: float, wind_speed: float, wind_direction: float) -> Dict[str, Any]:
    """Backwards-compatible legacy cone (kept for /risk-cone/{id} endpoint)."""
    ring = generate_spread_ellipse(lat, lon, wind_speed, wind_direction, hours=6)
    return ring.geojson


# ── Smoke plume ────────────────────────────────────────────────────────────────

# Indian AQI breakpoints for PM2.5 (µg/m³, 24-h avg per CPCB 2014)
_AQI_BREAKS = [
    (30,   "Good"),
    (60,   "Satisfactory"),
    (90,   "Moderate"),
    (120,  "Poor"),
    (250,  "Very Poor"),
    (1e9,  "Severe"),
]


def _pm25_to_aqi_category(pm25: float) -> str:
    for threshold, label in _AQI_BREAKS:
        if pm25 <= threshold:
            return label
    return "Severe"


def generate_smoke_plume(
    lat: float,
    lon: float,
    frp: float,
    wind_speed: float,
    wind_direction: float,
    distance_km: float = 20.0,
) -> SmokePlume:
    """
    Simplified Gaussian-plume PM2.5 estimate downwind of a fire.

    Q (emission rate) ~ FRP × 0.02 (g/s per MW, rough estimate from Ichoku 2003)
    σy = σz = PLUME_SIGMA_GROWTH × distance (Gaussian plume, neutral stability D)
    PM2.5(x) ≈ Q / (π × σ² × U) × exp(-y²/(2σ²))   at centreline (y=0)

    Plume polygon: a stretched ellipse along wind direction, width = 2σ at distance.
    """
    U = max(wind_speed / 3.6, 0.5)   # m/s
    Q = frp * 0.02                    # g/s
    x_m = distance_km * 1000
    sigma = config.PLUME_SIGMA_GROWTH * x_m
    pm25_at_x = Q / (math.pi * sigma ** 2 * U) * 1e6  # µg/m³ (convert g→µg, m³→µg/m³)
    pm25_at_x = min(pm25_at_x, 500.0)

    category = _pm25_to_aqi_category(pm25_at_x)

    # Build plume polygon (elongated ellipse, N=36 points)
    spread_rad = math.radians((wind_direction + 180) % 360)
    a_km = distance_km          # downwind extent
    b_km = max(sigma / 1000, 0.5)  # crosswind half-width at distance

    N = 36
    coords: List[List[float]] = []
    for i in range(N):
        θ = 2 * math.pi * i / N
        x_km = a_km * max(0.0, math.cos(θ))    # only downwind half
        y_km = b_km * math.sin(θ)
        e_km = x_km * math.sin(spread_rad) + y_km * math.cos(spread_rad)
        n_km = x_km * math.cos(spread_rad) - y_km * math.sin(spread_rad)
        coords.append([round(lon + _km_to_deg_lon(e_km, lat), 5),
                        round(lat + _km_to_deg_lat(n_km), 5)])
    coords.append(coords[0])

    geojson: Dict[str, Any] = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [coords]},
        "properties": {
            "pm25_ug_m3": round(pm25_at_x, 1),
            "aqi_category": category,
            "distance_km": distance_km,
            "frp_mw": frp,
        },
    }
    return SmokePlume(aqi_category=category, pm25_ug_m3=round(pm25_at_x, 1), geojson=geojson)


# ── Exposure analysis ─────────────────────────────────────────────────────────

def find_nearby_settlements(
    lat: float,
    lon: float,
    wind_speed: float,
    wind_direction: float,
    settlements: List[Dict],
    radius_km: float = 10.0,
) -> List[NearSettlement]:
    """
    Find settlements within radius_km of (lat, lon).
    Computes ETA assuming fire front travels at ROS toward the settlement.
    """
    spread_deg = (wind_direction + 180) % 360
    ros_kmh = config.SPREAD_ROS_BASE_KMH * (1.0 + 0.04 * wind_speed)
    results: List[NearSettlement] = []

    for s in settlements:
        dist = _haversine_km(lat, lon, s["lat"], s["lon"])
        if dist > radius_km:
            continue
        bearing = _bearing_deg(lat, lon, s["lat"], s["lon"])
        # ETA: only meaningful if fire is spreading toward settlement
        angle_diff = abs((bearing - spread_deg + 180) % 360 - 180)
        if angle_diff < 60 and ros_kmh > 0:
            eta = dist / ros_kmh
        else:
            eta = None
        results.append(NearSettlement(
            name=s["name"],
            state=s.get("state", ""),
            population=s.get("population", 0),
            distance_km=round(dist, 2),
            bearing_deg=round(bearing, 1),
            eta_hours=round(eta, 2) if eta is not None else None,
        ))

    results.sort(key=lambda x: x.distance_km)
    return results
