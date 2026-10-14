"""
Deterministic Synthetic VIIRS Hotspot Generator
================================================
Generates a realistic-looking VIIRS NRT CSV-schema dataset without calling any live API.

HONESTY NOTE:
  This file produces SIMULATED data. The schema exactly matches the NASA FIRMS VIIRS NRT
  CSV format so that swapping DATA_SOURCE=live requires zero frontend/pipeline changes.
  All spatial distributions, seasonal patterns, and physical correlations are modelled
  after published India fire-season climatology (ISFR, MODIS fire atlas, GFW) but are
  NOT real observations.

Usage (CLI):
  python -m backend.synthetic.generate --days 30 --seed 42 --out data/synthetic_hotspots.parquet

Usage (in-process):
  from backend.synthetic.generator import generate_hotspots
  df = generate_hotspots(days=30, seed=42)
"""

from __future__ import annotations

import math
import hashlib
import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# REGION DEFINITIONS
# Every region is characterised by its bounding box (W, S, E, N), dominant
# land cover, prevailing wind direction in degrees (meteorological FROM), a
# seasonal peak (month range, 1-12), and fire-intensity profile.
# ---------------------------------------------------------------------------

REGIONS: list[dict[str, Any]] = [
    {
        "name": "Uttarakhand/Himachal Pine Forests",
        "bbox": (76.5, 29.5, 81.5, 32.0),
        "land_cover": "pine_forest",
        "ndvi_range": (0.35, 0.65),
        "peak_months": list(range(3, 7)),          # Mar-Jun
        "mean_frp": 12.0,
        "bright_mean": 335.0,
        "mean_wind_kmh": 15.0,
        "wind_dir_deg": 270.0,   # westerly in spring
        "mean_temp_c": 22.0,
        "min_humidity": 20.0,
        "max_humidity": 55.0,
        "fire_density": 1.4,
        "state": "Uttarakhand",
    },
    {
        "name": "Odisha/Chhattisgarh Dry Deciduous",
        "bbox": (81.0, 19.0, 87.5, 24.5),
        "land_cover": "dry_deciduous",
        "ndvi_range": (0.15, 0.45),
        "peak_months": list(range(2, 6)),          # Feb-May
        "mean_frp": 20.0,
        "bright_mean": 340.0,
        "mean_wind_kmh": 18.0,
        "wind_dir_deg": 220.0,
        "mean_temp_c": 36.0,
        "min_humidity": 12.0,
        "max_humidity": 40.0,
        "fire_density": 1.8,
        "state": "Odisha",
    },
    {
        "name": "Madhya Pradesh/Maharashtra Mixed",
        "bbox": (75.0, 18.5, 82.5, 25.0),
        "land_cover": "mixed_forest",
        "ndvi_range": (0.20, 0.55),
        "peak_months": list(range(3, 6)),
        "mean_frp": 15.0,
        "bright_mean": 333.0,
        "mean_wind_kmh": 16.0,
        "wind_dir_deg": 240.0,
        "mean_temp_c": 34.0,
        "min_humidity": 15.0,
        "max_humidity": 45.0,
        "fire_density": 1.5,
        "state": "Madhya Pradesh",
    },
    {
        "name": "Western Ghats",
        "bbox": (74.0, 8.5, 77.5, 21.0),
        "land_cover": "tropical_forest",
        "ndvi_range": (0.50, 0.80),
        "peak_months": list(range(3, 5)),
        "mean_frp": 8.0,
        "bright_mean": 325.0,
        "mean_wind_kmh": 12.0,
        "wind_dir_deg": 250.0,
        "mean_temp_c": 30.0,
        "min_humidity": 25.0,
        "max_humidity": 65.0,
        "fire_density": 0.8,
        "state": "Kerala",
    },
    {
        "name": "Northeast Jhum Cultivation",
        "bbox": (91.0, 22.0, 97.5, 27.5),
        "land_cover": "jhum_agriculture",
        "ndvi_range": (0.10, 0.40),
        "peak_months": list(range(3, 5)),
        "mean_frp": 25.0,
        "bright_mean": 345.0,
        "mean_wind_kmh": 10.0,
        "wind_dir_deg": 180.0,
        "mean_temp_c": 28.0,
        "min_humidity": 30.0,
        "max_humidity": 60.0,
        "fire_density": 2.0,
        "state": "Assam",
    },
    {
        "name": "Punjab/Haryana Crop Residue",
        "bbox": (74.0, 29.5, 77.5, 32.0),
        "land_cover": "cropland",
        "ndvi_range": (0.05, 0.25),
        "peak_months": [10, 11],                   # Oct-Nov stubble
        "mean_frp": 30.0,
        "bright_mean": 348.0,
        "mean_wind_kmh": 20.0,
        "wind_dir_deg": 285.0,
        "mean_temp_c": 25.0,
        "min_humidity": 30.0,
        "max_humidity": 60.0,
        "fire_density": 2.5,
        "state": "Punjab",
    },
]

# ---------------------------------------------------------------------------
# Ocean mask — simplified coastal bounding boxes to reject sea points.
# These are conservative land-only checks; any point inside India's land
# polygon is accepted. We use a coarse exclusion: points west of 68°E
# south of 22°N (Arabian Sea) and east of 92°E south of 21°N (Bay of Bengal)
# are likely ocean.
# ---------------------------------------------------------------------------

def _is_on_land(lat: float, lon: float) -> bool:
    """
    Coarse land check for the Indian subcontinent.
    Rejects obvious ocean cells; false positives (coastal land) are acceptable
    since the generator clusters fires inside region bboxes which are on land.
    """
    # Arabian Sea west coast rough exclusion
    if lon < 68.5 and lat < 23.0:
        return False
    # Bay of Bengal east rough exclusion
    if lon > 92.5 and lat < 21.0:
        return False
    # Sri Lanka / southern ocean
    if lat < 8.0:
        return False
    # Far north (not India)
    if lat > 37.5:
        return False
    return True


# ---------------------------------------------------------------------------
# SEASONAL WEIGHT
# ---------------------------------------------------------------------------

def _seasonal_weight(month: int, peak_months: list[int]) -> float:
    """
    Returns a weight in [0.1, 1.0] based on how close `month` is to the
    region's peak fire season. Uses a Gaussian bell around peak midpoint.
    """
    if not peak_months:
        return 0.5
    mid = np.mean(peak_months)
    dist = min(abs(month - mid), 12 - abs(month - mid))  # circular month distance
    weight = math.exp(-(dist ** 2) / (2 * 2.0 ** 2))
    return max(0.1, weight)


# ---------------------------------------------------------------------------
# CORE GENERATOR
# ---------------------------------------------------------------------------

def generate_hotspots(
    days: int = 30,
    seed: int = 42,
    reference_date: date | None = None,
) -> pd.DataFrame:
    """
    Generate a synthetic VIIRS NRT hotspot DataFrame.

    Parameters
    ----------
    days : int
        Number of days to simulate (rolling window ending at reference_date).
    seed : int
        RNG seed for full reproducibility.
    reference_date : date | None
        End date of simulation window. Defaults to today.

    Returns
    -------
    pd.DataFrame with columns matching the VIIRS NRT schema plus enrichment fields.

    Schema columns (VIIRS NRT):
        latitude, longitude, bright_ti4, bright_ti5, scan, track, acq_date,
        acq_time, satellite, instrument, confidence, version, frp, daynight

    Enrichment columns:
        wind_speed_kmh, wind_dir_deg, temperature_c, humidity_pct,
        ndvi, land_cover, state, source, cluster_id, weather_source,
        persistence_days, region
    """
    rng = np.random.default_rng(seed)
    ref = reference_date or date.today()
    start = ref - timedelta(days=days - 1)
    date_range = [start + timedelta(days=i) for i in range(days)]

    records: list[dict[str, Any]] = []

    for region in REGIONS:
        bbox_w, bbox_s, bbox_e, bbox_n = region["bbox"]
        peak_months = region["peak_months"]

        for day in date_range:
            month = day.month
            season_w = _seasonal_weight(month, peak_months)

            # Number of fire clusters today in this region
            expected_clusters = max(0, int(rng.poisson(region["fire_density"] * season_w * 2)))

            for c_idx in range(expected_clusters):
                cluster_id = f"{region['name'][:4].upper()}_{day.strftime('%Y%m%d')}_{c_idx:02d}"

                # Cluster centre
                c_lat = float(rng.uniform(bbox_s, bbox_n))
                c_lon = float(rng.uniform(bbox_w, bbox_e))

                # Persistence: cluster lives 1-6 days; drift slightly downwind
                persistence = int(rng.integers(1, 7))

                # Number of hotspot points in cluster (3-25)
                n_pts = int(rng.integers(3, 26))

                # Cluster spread (sigma) in degrees (~1-5 km)
                sigma = float(rng.uniform(0.008, 0.045))

                # Weather for this cluster-day
                u_wind = float(rng.gamma(
                    shape=(region["mean_wind_kmh"] / 5.0) ** 2 / (region["mean_wind_kmh"] / 5.0),
                    scale=region["mean_wind_kmh"] / ((region["mean_wind_kmh"] / 5.0) ** 2 / (region["mean_wind_kmh"] / 5.0))
                ))
                u_wind = float(np.clip(u_wind, 0.5, 80.0))

                wind_dir = float((region["wind_dir_deg"] + rng.normal(0, 25)) % 360)
                temp_c = float(region["mean_temp_c"] + rng.normal(0, 3))
                humidity = float(np.clip(
                    rng.uniform(region["min_humidity"], region["max_humidity"]) - season_w * 10,
                    5.0, 95.0
                ))

                for p_idx in range(n_pts):
                    lat = float(rng.normal(c_lat, sigma))
                    lon = float(rng.normal(c_lon, sigma))

                    # Reject ocean points
                    if not _is_on_land(lat, lon):
                        continue

                    # NDVI: lower in dry season, varies by land cover
                    ndvi_min, ndvi_max = region["ndvi_range"]
                    ndvi_range_mid = (ndvi_min + ndvi_max) / 2
                    ndvi = float(np.clip(
                        rng.normal(ndvi_range_mid - season_w * 0.1, 0.05),
                        ndvi_min, ndvi_max
                    ))

                    # Fire intensity: brighter when hotter, drier, windier
                    dryness_factor = (1 - humidity / 100) * (1 - ndvi)
                    brightness_ti4 = float(np.clip(
                        rng.normal(region["bright_mean"] + dryness_factor * 20, 6),
                        300.0, 367.0
                    ))
                    brightness_ti5 = float(np.clip(
                        brightness_ti4 - rng.uniform(2, 8),
                        298.0, 362.0
                    ))

                    # FRP: log-normal, correlated with brightness
                    frp_mu = math.log(region["mean_frp"] * (1 + dryness_factor))
                    frp = float(np.clip(rng.lognormal(frp_mu, 0.6), 0.5, 150.0))

                    # Confidence: derived from brightness and frp; day fires more often "h"
                    b_norm = (brightness_ti4 - 300) / 67.0
                    if b_norm > 0.65 and frp > 15:
                        confidence = "h"
                    elif b_norm < 0.30 or frp < 3:
                        confidence = "l"
                    else:
                        confidence = "n"

                    # Satellite passes ~01:30 and ~13:30 local (UTC offset +5:30)
                    # Night pass: 01:30 IST = 20:00 UTC prev day → we simplify to 0130 UTC
                    # Day pass:   13:30 IST = 08:00 UTC
                    pass_choice = rng.integers(0, 2)
                    acq_time_utc = "0130" if pass_choice == 0 else "0800"
                    daynight = "N" if pass_choice == 0 else "D"
                    satellite = rng.choice(["N", "N20", "N21"])

                    # Scan/track (swath geometry parameters — typical VIIRS values)
                    scan = float(np.clip(rng.normal(0.42, 0.08), 0.3, 0.75))
                    track = float(np.clip(rng.normal(0.42, 0.08), 0.3, 0.75))

                    # Diurnal temp adjustment
                    if daynight == "N":
                        temp_adj = temp_c - float(rng.uniform(4, 8))
                    else:
                        temp_adj = temp_c + float(rng.uniform(2, 5))

                    records.append({
                        # --- VIIRS NRT schema ---
                        "latitude": round(lat, 4),
                        "longitude": round(lon, 4),
                        "bright_ti4": round(brightness_ti4, 1),
                        "bright_ti5": round(brightness_ti5, 1),
                        "scan": round(scan, 3),
                        "track": round(track, 3),
                        "acq_date": day.isoformat(),
                        "acq_time": acq_time_utc,
                        "satellite": str(satellite),
                        "instrument": "VIIRS",
                        "confidence": confidence,
                        "version": "2.0NRT",
                        "frp": round(frp, 2),
                        "daynight": daynight,
                        # --- backwards-compat alias for existing code ---
                        "brightness": round(brightness_ti4, 1),
                        # --- enrichment ---
                        "wind_speed_kmh": round(u_wind, 1),
                        "wind_dir_deg": round(wind_dir, 1),
                        "temperature_c": round(temp_adj, 1),
                        "humidity_pct": round(humidity, 1),
                        "ndvi": round(ndvi, 3),
                        "land_cover": region["land_cover"],
                        "state": region["state"],
                        "region": region["name"],
                        "source": "synthetic",
                        "weather_source": "synthetic",
                        "weather_ok": True,
                        "cluster_id": cluster_id,
                        "persistence_days": persistence,
                    })

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Stable deterministic ID per row
    df["id"] = df.apply(
        lambda r: hashlib.md5(
            f"{r['latitude']}_{r['longitude']}_{r['acq_date']}_{r['acq_time']}_{r['cluster_id']}".encode()
        ).hexdigest(),
        axis=1,
    )

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# IN-MEMORY CACHE (used by main.py at startup)
# ---------------------------------------------------------------------------
_cache: pd.DataFrame | None = None
_cache_seed: int | None = None
_cache_days: int | None = None


def get_cached_hotspots(days: int = 30, seed: int = 42) -> pd.DataFrame:
    """Return cached synthetic dataset, regenerating only when params change."""
    global _cache, _cache_seed, _cache_days
    if _cache is None or _cache_seed != seed or _cache_days != days:
        _cache = generate_hotspots(days=days, seed=seed)
        _cache_seed = seed
        _cache_days = days
    return _cache


# ---------------------------------------------------------------------------
# CLI ENTRY POINT
# ---------------------------------------------------------------------------

def _cli() -> None:
    import argparse, sys

    parser = argparse.ArgumentParser(description="Generate synthetic VIIRS hotspot dataset")
    parser.add_argument("--days", type=int, default=30, help="Number of days to simulate")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--out", type=str, default="data/synthetic_hotspots.parquet", help="Output path (.parquet or .csv)")
    args = parser.parse_args()

    print(f"Generating {args.days}-day synthetic dataset (seed={args.seed})…")
    df = generate_hotspots(days=args.days, seed=args.seed)
    print(f"  → {len(df)} hotspots across {df['state'].nunique()} states")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if str(out_path).endswith(".csv"):
        df.to_csv(out_path, index=False)
    else:
        try:
            df.to_parquet(out_path, index=False)
        except ImportError:
            csv_path = out_path.with_suffix(".csv")
            df.to_csv(csv_path, index=False)
            print(f"  pyarrow not installed; saved as CSV → {csv_path}")
            sys.exit(0)
    print(f"  Saved → {out_path}")


if __name__ == "__main__":
    _cli()
