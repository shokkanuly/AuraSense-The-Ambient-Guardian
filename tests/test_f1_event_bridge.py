"""
F1 verification — also the first brick of the F3 test harness.

End-to-end proof that inserting an ``events`` row fires the Postgres
LISTEN/NOTIFY -> WebSocket bridge that the dashboard's "Live" badge depends on.
This is the bug that was silently broken (the listener was started from a
router ``startup`` hook that FastAPI never runs); the test fails if it regresses.

Requires the docker-compose TimescaleDB reachable at DATABASE_URL (host port
5434). Skips cleanly if the DB is unreachable so the suite still runs offline.
"""
import os
import time
import uuid
import json
import asyncio

import asyncpg
import pytest
from fastapi.testclient import TestClient

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/aurasense"
)


def _db_reachable() -> bool:
    async def _check():
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
            return True
        except Exception:
            return False

    return asyncio.run(_check())


pytestmark = pytest.mark.skipif(
    not _db_reachable(), reason=f"TimescaleDB not reachable at {DATABASE_URL}"
)


async def _seed_node_and_insert_event(event_id: str, node_id: str) -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # events.node_id has a FK to nodes(node_id), so seed the node first.
        await conn.execute(
            """
            INSERT INTO nodes (node_id, type, last_seen, firmware_version, status)
            VALUES ($1, 'motion', $2, '1.0.0', 'ONLINE')
            ON CONFLICT (node_id) DO NOTHING
            """,
            node_id,
            int(time.time()),
        )
        await conn.execute(
            """
            INSERT INTO events (event_id, ts, type, severity, node_id, payload, acknowledged)
            VALUES ($1, now(), 'fall_detected', 'CRITICAL', $2, $3, FALSE)
            """,
            event_id,
            node_id,
            json.dumps({"description": "F1 bridge test fall"}),
        )
    finally:
        await conn.close()


@pytest.mark.timeout(20)
def test_event_insert_is_broadcast_over_websocket():
    from hub.services.api.main import app  # imported after DATABASE_URL is set

    with TestClient(app) as client:  # runs the app lifespan: DB pool + PG listener
        time.sleep(1.0)  # let the listener register on 'events_channel'
        with client.websocket_connect("/ws/v1/events") as ws:
            time.sleep(0.3)  # ensure this client is registered before we insert
            event_id = str(uuid.uuid4())
            node_id = f"node_test_{event_id[:8]}"
            asyncio.run(_seed_node_and_insert_event(event_id, node_id))

            frame = ws.receive_json()  # bounded by the 20s marker if the bridge is broken
            assert frame["type"] == "event_notification"
            assert frame["data"]["event_id"] == event_id
            assert frame["data"]["type"] == "fall_detected"
            assert frame["data"]["severity"] == "CRITICAL"
