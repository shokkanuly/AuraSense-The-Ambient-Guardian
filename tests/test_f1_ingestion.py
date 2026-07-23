"""
F1 verification for the ingestion service:
  * paho-mqtt v2 callback API is used (regression guard for the version bump),
  * a validated payload is written to TimescaleDB, upserting the node
    (exercises the Pydantic ``.model_dump()`` change and the SQL path).

The DB write test skips cleanly if TimescaleDB is unreachable.
"""
import os
import time
import uuid
import json
import asyncio
import inspect

import asyncpg
import pytest

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from hub.services.ingestion import IngestionService

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


def test_on_connect_uses_paho_v2_signature():
    # paho-mqtt v2's on_connect passes (client, userdata, flags, reason_code, properties).
    params = list(inspect.signature(IngestionService.on_mqtt_connect).parameters)
    assert params == ["self", "client", "userdata", "flags", "reason_code", "properties"]


@pytest.mark.skipif(not _db_reachable(), reason=f"TimescaleDB not reachable at {DATABASE_URL}")
def test_ingest_message_writes_reading_and_upserts_node():
    node_id = f"node_ingest_{uuid.uuid4().hex[:8]}"
    topic = f"aurasense/nodes/{node_id}/motion"
    payload = {
        "ts": int(time.time()),
        "features": {
            "presence": True,
            "breathing_rate": 15.5,
            "fall_detected": False,
            "point_cloud_summary": [0.1, 0.2, 0.3],
        },
    }

    async def _run():
        svc = IngestionService()
        await svc.connect_db()
        try:
            await svc.ingest_message({"topic": topic, "payload": json.dumps(payload)})

            async with svc.db_pool.acquire() as conn:
                node = await conn.fetchrow(
                    "SELECT type, status FROM nodes WHERE node_id = $1", node_id
                )
                reading = await conn.fetchrow(
                    "SELECT type, features FROM sensor_readings WHERE node_id = $1", node_id
                )
        finally:
            await svc.db_pool.close()
        return node, reading

    node, reading = asyncio.run(_run())
    assert node is not None and node["type"] == "motion" and node["status"] == "ONLINE"
    assert reading is not None and reading["type"] == "motion"
    feats = json.loads(reading["features"])
    assert feats["breathing_rate"] == 15.5 and feats["presence"] is True
