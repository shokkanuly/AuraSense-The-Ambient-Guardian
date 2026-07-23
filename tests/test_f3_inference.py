"""
F3 verification — the detection pipeline and its guards, driven by simulator data.

  * A simulated ``fall`` motion reading, ingested and run through fall detection,
    produces exactly one CRITICAL event, and a second detection pass is throttled
    (no duplicate) — the false-alarm guard the vision cares about.
  * An invalid sensor payload is rejected by ingestion and never written.

Requires the docker-compose TimescaleDB; skips cleanly if unreachable.
"""
import os
import json
import time
import uuid
import asyncio

import asyncpg
import pytest

from tools.sim.generator import build_payload
from hub.services.ingestion import IngestionService
from hub.services.inference import InferenceService

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


def test_fall_pipeline_raises_one_critical_and_throttles():
    node_id = f"node_fall_{uuid.uuid4().hex[:8]}"

    async def _run():
        ing = IngestionService()
        await ing.connect_db()
        inf = InferenceService()
        await inf.connect_db()
        try:
            payload = build_payload("motion", "fall")
            await ing.ingest_message(
                {"topic": f"aurasense/nodes/{node_id}/motion", "payload": json.dumps(payload)}
            )
            async with inf.db_pool.acquire() as conn:
                await inf.run_fall_detection(conn, node_id)
                await inf.run_fall_detection(conn, node_id)  # should be throttled
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM events WHERE node_id=$1 AND type='fall_detected'",
                    node_id,
                )
                severity = await conn.fetchval(
                    "SELECT severity FROM events WHERE node_id=$1 AND type='fall_detected' LIMIT 1",
                    node_id,
                )
            return count, severity
        finally:
            await ing.db_pool.close()
            await inf.db_pool.close()

    count, severity = asyncio.run(_run())
    assert count == 1, f"expected exactly one fall event (throttled), got {count}"
    assert severity == "CRITICAL"


def test_ingestion_rejects_invalid_payload():
    node_id = f"node_bad_{uuid.uuid4().hex[:8]}"

    async def _run():
        ing = IngestionService()
        await ing.connect_db()
        try:
            # motion payload missing the required breathing_rate -> ValidationError
            bad = {"ts": int(time.time()), "features": {"presence": True, "fall_detected": False}}
            await ing.ingest_message(
                {"topic": f"aurasense/nodes/{node_id}/motion", "payload": json.dumps(bad)}
            )
            async with ing.db_pool.acquire() as conn:
                readings = await conn.fetchval(
                    "SELECT COUNT(*) FROM sensor_readings WHERE node_id=$1", node_id
                )
            return readings
        finally:
            await ing.db_pool.close()

    assert asyncio.run(_run()) == 0
