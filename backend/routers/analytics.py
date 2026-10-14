"""
/analytics router
GET /analytics?start=&end=
Returns aggregated stats for Recharts dashboard.
"""

from __future__ import annotations
from collections import Counter
from fastapi import APIRouter, Query
from typing import Optional

import config
from models import AnalyticsResponse, DailyCount, RiskLevelCount, StateCount, TopHotspot
from synthetic.generator import get_cached_hotspots
from routers.hotspots import _build_hotspot_from_row
from synthetic.settlements import load_settlements

router = APIRouter()


@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(
    start: Optional[str] = Query(None),
    end:   Optional[str] = Query(None),
):
    settlements = load_settlements()
    df = get_cached_hotspots(days=config.SYNTHETIC_DAYS, seed=config.SYNTHETIC_SEED)
    rows = df.to_dict(orient="records")

    if start:
        rows = [r for r in rows if r.get("acq_date", "9999") >= start]
    if end:
        rows = [r for r in rows if r.get("acq_date", "0000") <= end]

    hotspots = [_build_hotspot_from_row(r, settlements) for r in rows]

    # Fires per day
    day_counter: Counter = Counter(h.acq_date for h in hotspots)
    fires_per_day = [DailyCount(date=d, count=c) for d, c in sorted(day_counter.items())]

    # Risk level distribution
    level_counter: Counter = Counter(h.risk_level or "Low" for h in hotspots)
    risk_distribution = [
        RiskLevelCount(level=lvl, count=cnt)
        for lvl, cnt in level_counter.items()
    ]

    # State counts
    state_counter: Counter = Counter(h.state or "Unknown" for h in hotspots)
    state_counts = [
        StateCount(state=st, count=cnt)
        for st, cnt in state_counter.most_common(10)
    ]

    # Top 10 riskiest
    top = sorted(hotspots, key=lambda h: h.risk_score or 0, reverse=True)[:10]
    top_hotspots = [
        TopHotspot(
            id=h.id,
            latitude=h.latitude,
            longitude=h.longitude,
            risk_score=h.risk_score or 0,
            state=h.state,
            acq_date=h.acq_date,
        )
        for h in top
    ]

    return AnalyticsResponse(
        fires_per_day=fires_per_day,
        risk_distribution=risk_distribution,
        state_counts=state_counts,
        top_hotspots=top_hotspots,
    )
