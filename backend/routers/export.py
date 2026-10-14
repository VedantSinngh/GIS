"""
/export router
GET /export/csv and GET /export/geojson
Download the filtered hotspot dataset.
"""

from __future__ import annotations

import io
import json
import csv as csv_module
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import Optional

import config
from synthetic.generator import get_cached_hotspots
from routers.hotspots import _build_hotspot_from_row
from synthetic.settlements import load_settlements

router = APIRouter()


@router.get("/export/csv")
def export_csv(
    start: Optional[str] = Query(None),
    end:   Optional[str] = Query(None),
    min_risk: float = Query(0),
):
    """Download filtered hotspots as CSV."""
    settlements = load_settlements()
    df = get_cached_hotspots(days=config.SYNTHETIC_DAYS, seed=config.SYNTHETIC_SEED)
    rows = df.to_dict(orient="records")

    if start:
        rows = [r for r in rows if r.get("acq_date", "9999") >= start]
    if end:
        rows = [r for r in rows if r.get("acq_date", "0000") <= end]

    hotspots = [_build_hotspot_from_row(r, settlements) for r in rows]
    if min_risk > 0:
        hotspots = [h for h in hotspots if (h.risk_score or 0) >= min_risk]

    output = io.StringIO()
    fields = [
        "id", "latitude", "longitude", "brightness", "frp", "confidence",
        "acq_date", "acq_time", "satellite", "daynight", "wind_speed",
        "wind_direction", "temperature_c", "humidity_pct", "ndvi",
        "land_cover", "state", "region", "risk_score", "risk_level", "source",
    ]
    writer = csv_module.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for h in hotspots:
        writer.writerow(h.model_dump(include=set(fields)))

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=wildfire_hotspots.csv"},
    )


@router.get("/export/geojson")
def export_geojson(
    start: Optional[str] = Query(None),
    end:   Optional[str] = Query(None),
    min_risk: float = Query(0),
):
    """Download filtered hotspots as GeoJSON FeatureCollection."""
    settlements = load_settlements()
    df = get_cached_hotspots(days=config.SYNTHETIC_DAYS, seed=config.SYNTHETIC_SEED)
    rows = df.to_dict(orient="records")

    if start:
        rows = [r for r in rows if r.get("acq_date", "9999") >= start]
    if end:
        rows = [r for r in rows if r.get("acq_date", "0000") <= end]

    hotspots = [_build_hotspot_from_row(r, settlements) for r in rows]
    if min_risk > 0:
        hotspots = [h for h in hotspots if (h.risk_score or 0) >= min_risk]

    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [h.longitude, h.latitude]},
            "properties": {
                "id": h.id,
                "brightness": h.brightness,
                "frp": h.frp,
                "confidence": h.confidence,
                "acq_date": h.acq_date,
                "risk_score": h.risk_score,
                "risk_level": h.risk_level,
                "state": h.state,
                "source": h.source,
            },
        }
        for h in hotspots
    ]

    geojson = json.dumps({"type": "FeatureCollection", "features": features})
    return StreamingResponse(
        io.BytesIO(geojson.encode()),
        media_type="application/geo+json",
        headers={"Content-Disposition": "attachment; filename=wildfire_hotspots.geojson"},
    )
