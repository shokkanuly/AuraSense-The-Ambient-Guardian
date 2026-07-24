import os
import json
import sys
from datetime import datetime, timedelta, timezone

import asyncpg
from fastapi import APIRouter, Depends, Query

# Ensure import of shared types
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))
from shared.types.api_types import GenericResponseEnvelope, AnomalyScorePayload
from hub.services.api.main import get_db

router = APIRouter()


@router.get("/energy", response_model=GenericResponseEnvelope)
async def get_energy(
    minutes: int = Query(60, ge=1, le=1440, description="Look-back window in minutes"),
    conn: asyncpg.Connection = Depends(get_db),
):
    """
    Recent NILM appliance-disaggregation points, one per inference cycle, for the
    dashboard's energy chart. Each point flattens the appliance breakdown so the
    frontend can plot it directly.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    rows = await conn.fetch(
        """
        SELECT ts, node_id, appliances, total_w
        FROM energy_disaggregation
        WHERE ts >= $1
        ORDER BY ts ASC
        """,
        cutoff,
    )
    points = []
    appliance_keys: set[str] = set()
    for r in rows:
        appliances = json.loads(r["appliances"])
        appliance_keys.update(appliances.keys())
        points.append(
            {
                "ts": int(r["ts"].timestamp()),
                "node_id": r["node_id"],
                "total_w": r["total_w"],
                **appliances,
            }
        )
    return GenericResponseEnvelope(
        data=points,
        meta={"appliances": sorted(appliance_keys), "minutes": minutes, "count": len(points)},
    )


@router.get("/anomaly-scores", response_model=GenericResponseEnvelope)
async def get_anomaly_scores(
    minutes: int = Query(60, ge=1, le=1440, description="Look-back window in minutes"),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Recent behavioral anomaly scores (from the anomaly detector)."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    rows = await conn.fetch(
        """
        SELECT ts, model, score, context
        FROM anomaly_scores
        WHERE ts >= $1
        ORDER BY ts ASC
        """,
        cutoff,
    )
    scores = [
        AnomalyScorePayload(
            ts=int(r["ts"].timestamp()),
            model=r["model"],
            score=r["score"],
            context=json.loads(r["context"]),
        )
        for r in rows
    ]
    return GenericResponseEnvelope(
        data=scores, meta={"minutes": minutes, "count": len(scores)}
    )
