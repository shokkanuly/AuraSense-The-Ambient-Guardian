"""
F4 verification — the real data endpoints.

  * /api/v1/energy and /api/v1/anomaly-scores require a token (F2), and
  * /api/v1/energy returns the NILM disaggregation that inference persisted,
    /api/v1/anomaly-scores returns persisted scores — real data, no mocks.

Requires the docker-compose TimescaleDB; skips cleanly if unreachable.
"""
import os
import json
import uuid
import asyncio

import asyncpg
import pytest
from fastapi.testclient import TestClient

from hub.services.api.security import PAIRING_CODE
from hub.services.ingestion import IngestionService
from hub.services.inference import InferenceService
from tools.sim.generator import build_payload

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


@pytest.fixture(scope="module")
def client():
    from hub.services.api.main import app

    with TestClient(app) as c:
        yield c


def _token(client) -> str:
    resp = client.post("/api/v1/pair", json={"pairing_code": PAIRING_CODE})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def test_data_endpoints_require_token(client):
    assert client.get("/api/v1/energy").status_code == 401
    assert client.get("/api/v1/anomaly-scores").status_code == 401


def test_energy_returns_persisted_disaggregation(client):
    node_id = f"node_power_{uuid.uuid4().hex[:8]}"

    async def _setup():
        ing = IngestionService()
        await ing.connect_db()
        inf = InferenceService()
        await inf.connect_db()
        try:
            for _ in range(3):
                payload = build_payload("power", "microwave")
                await ing.ingest_message(
                    {"topic": f"aurasense/nodes/{node_id}/power", "payload": json.dumps(payload)}
                )
            async with inf.db_pool.acquire() as conn:
                await inf.run_nilm(conn, node_id)  # persists an energy_disaggregation row
        finally:
            await ing.db_pool.close()
            await inf.db_pool.close()

    asyncio.run(_setup())

    resp = client.get(
        "/api/v1/energy?minutes=60", headers={"Authorization": f"Bearer {_token(client)}"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    mine = [pt for pt in body["data"] if pt["node_id"] == node_id]
    assert mine, "expected a persisted energy point for the node"
    for key in ("refrigerator", "microwave", "hvac", "other"):
        assert key in mine[0]
    assert "appliances" in body["meta"]


def test_anomaly_scores_returns_persisted_rows(client):
    marker = f"test_model_{uuid.uuid4().hex[:6]}"

    async def _insert():
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute(
                "INSERT INTO anomaly_scores (ts, model, score, context) VALUES (now(), $1, 0.5, $2)",
                marker,
                json.dumps({"note": "f4-test"}),
            )
        finally:
            await conn.close()

    asyncio.run(_insert())

    resp = client.get(
        "/api/v1/anomaly-scores?minutes=60",
        headers={"Authorization": f"Bearer {_token(client)}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert any(s["model"] == marker for s in data)
