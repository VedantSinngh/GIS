"""
Wildfire & Air Quality Risk Monitor — FastAPI Backend
======================================================
Endpoints:
  GET /hotspots            — core data feed (synthetic | live | hybrid)
  GET /spread/{id}         — elliptical fire-spread rings
  GET /exposure/{id}       — settlement exposure + ETA
  GET /alerts              — auto-generated sorted alert list
  GET /analytics           — aggregated stats for dashboard
  GET /export/csv          — CSV download
  GET /export/geojson      — GeoJSON download
  GET /risk-cone/{id}      — legacy cone (backwards compat)
  GET /healthz             — health check
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from routers import hotspots, spread, exposure, analytics, export

app = FastAPI(
    title="Wildfire Risk Monitor API",
    description=(
        "Heuristic decision-support tool for wildfire spread risk in India. "
        "DATA_SOURCE=synthetic means all hotspot data is simulated; algorithms and "
        "formulas are real. Set DATA_SOURCE=live for NASA FIRMS."
    ),
    version="2.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Fix: allow_credentials must be False when allow_origins includes "*"
_origins = config.ALLOWED_ORIGINS
_allow_credentials = "*" not in _origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(hotspots.router)
app.include_router(spread.router)
app.include_router(exposure.router)
app.include_router(analytics.router)
app.include_router(export.router)


# ── Legacy endpoint (backwards compat with old frontend) ─────────────────────
from fastapi import Query as Q
from typing import Any, Dict

@app.get("/risk-cone/{hotspot_id}")
def legacy_risk_cone(
    hotspot_id: str,
    lat: float = Q(...),
    lon: float = Q(...),
    wind_speed: float = Q(...),
    wind_direction: float = Q(...),
) -> Dict[str, Any]:
    """Legacy cone endpoint — now returns an Anderson 1983 ellipse as GeoJSON."""
    from services.risk import generate_risk_cone
    feature = generate_risk_cone(lat, lon, wind_speed, wind_direction)
    return {"type": "FeatureCollection", "features": [feature]}


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/healthz")
def health() -> Dict[str, str]:
    return {"status": "ok", "data_source": config.DATA_SOURCE}


# ── Startup: warm the synthetic cache ─────────────────────────────────────────
@app.on_event("startup")
def warm_cache() -> None:
    if config.DATA_SOURCE in ("synthetic", "hybrid"):
        from synthetic.generator import get_cached_hotspots
        df = get_cached_hotspots(days=config.SYNTHETIC_DAYS, seed=config.SYNTHETIC_SEED)
        print(f"[startup] Synthetic cache warmed: {len(df)} hotspots (seed={config.SYNTHETIC_SEED}, days={config.SYNTHETIC_DAYS})")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
