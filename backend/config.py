"""
Central configuration for Wildfire Risk Monitor backend.

DATA_SOURCE modes
-----------------
  synthetic  – always use the seeded generator; no live API calls.
  live       – use NASA FIRMS + Open-Meteo; raise if they fail.
  hybrid     – try live FIRMS first; fall back to synthetic on failure or DEMO_KEY.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── NASA FIRMS ──────────────────────────────────────────────────────────────
FIRMS_MAP_KEY: str = os.getenv("FIRMS_MAP_KEY", "DEMO_KEY")

# ── Data Source ──────────────────────────────────────────────────────────────
# "synthetic" | "live" | "hybrid"
DATA_SOURCE: str = os.getenv("DATA_SOURCE", "synthetic")

# ── Synthetic Generator ──────────────────────────────────────────────────────
SYNTHETIC_SEED: int = int(os.getenv("SYNTHETIC_SEED", "42"))
SYNTHETIC_DAYS: int = int(os.getenv("SYNTHETIC_DAYS", "30"))

# ── Default bounding box (India) ─────────────────────────────────────────────
DEFAULT_BBOX: str = os.getenv("DEFAULT_BBOX", "68.1,6.7,97.4,35.5")

# ── CORS ─────────────────────────────────────────────────────────────────────
# Comma-separated list of allowed origins. "*" means allow all (no credentials).
ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if o.strip()
]

# ── Risk-Score Weights (must sum to 1.0) ─────────────────────────────────────
RISK_WEIGHT_INTENSITY:    float = float(os.getenv("RISK_WEIGHT_INTENSITY",    "0.30"))
RISK_WEIGHT_WIND:         float = float(os.getenv("RISK_WEIGHT_WIND",         "0.25"))
RISK_WEIGHT_FUEL:         float = float(os.getenv("RISK_WEIGHT_FUEL",         "0.25"))
RISK_WEIGHT_EXPOSURE:     float = float(os.getenv("RISK_WEIGHT_EXPOSURE",     "0.10"))
RISK_WEIGHT_PERSISTENCE:  float = float(os.getenv("RISK_WEIGHT_PERSISTENCE",  "0.10"))

# ── Spread Ellipse ────────────────────────────────────────────────────────────
# Anderson 1983 / FARSITE-style: LBR = 1 + 0.125 * U  (U = wind speed km/h)
# Backing rate of spread (km/h) at zero wind
SPREAD_ROS_BASE_KMH: float = float(os.getenv("SPREAD_ROS_BASE_KMH", "0.5"))

# ── Smoke Plume ───────────────────────────────────────────────────────────────
# Gaussian plume sigma growth rate (m / m of downwind distance)
PLUME_SIGMA_GROWTH: float = float(os.getenv("PLUME_SIGMA_GROWTH", "0.12"))

# ── Exposure ──────────────────────────────────────────────────────────────────
EXPOSURE_RADIUS_KM: float = float(os.getenv("EXPOSURE_RADIUS_KM", "10.0"))
EXPOSURE_RADIUS_WIDE_KM: float = float(os.getenv("EXPOSURE_RADIUS_WIDE_KM", "25.0"))
