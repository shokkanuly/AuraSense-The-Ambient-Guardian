import os
import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
import asyncpg
from typing import List, Optional
import sys

# Ensure import of shared types
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))
from shared.types.api_types import EventPayload, GenericResponseEnvelope
from hub.services.api.main import get_db

router = APIRouter()

@router.get("/events", response_model=GenericResponseEnvelope)
async def list_events(
    severity: Optional[str] = Query(None, description="Filter by severity: INFO, WARNING, CRITICAL"),
    node_id: Optional[str] = Query(None, description="Filter by node ID"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Retrieve historical events/alerts, with optional filters for node, severity, and acknowledgment state.
    """
    query = "SELECT event_id, ts, type, severity, node_id, payload, acknowledged FROM events WHERE 1=1"
    params = []
    param_idx = 1

    if severity:
        query += f" AND severity = ${param_idx}"
        params.append(severity)
        param_idx += 1
    
    if node_id:
        query += f" AND node_id = ${param_idx}"
        params.append(node_id)
        param_idx += 1

    if acknowledged is not None:
        query += f" AND acknowledged = ${param_idx}"
        params.append(acknowledged)
        param_idx += 1

    query += " ORDER BY ts DESC LIMIT 100"

    rows = await conn.fetch(query, *params)
    events = []
    for r in rows:
        events.append(EventPayload(
            event_id=r["event_id"],
            ts=int(r["ts"].timestamp()),
            type=r["type"],
            severity=r["severity"],
            node_id=r["node_id"],
            payload=json.loads(r["payload"]),
            acknowledged=r["acknowledged"]
        ))
    return GenericResponseEnvelope(data=events)

@router.post("/events/{event_id}/ack", response_model=GenericResponseEnvelope)
async def acknowledge_event(event_id: str, conn: asyncpg.Connection = Depends(get_db)):
    """
    Acknowledge a critical/warning alert to silence alarms on client dashboards.
    """
    result = await conn.execute(
        "UPDATE events SET acknowledged = TRUE WHERE event_id = $1",
        event_id
    )
    if result == "UPDATE 0":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
    return GenericResponseEnvelope(data={"message": f"Event {event_id} acknowledged successfully"})
