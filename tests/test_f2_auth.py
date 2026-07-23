"""
F2 verification — pairing-based auth on the /api/v1 REST routers.

Covers the stage's "Done when": GET /api/v1/nodes is 401 without a token and
200 with a token obtained from the pairing flow. Also checks the pairing
happy/sad paths and that a garbage token is rejected.

Requires the docker-compose TimescaleDB (the app lifespan opens the pool on
startup); skips cleanly if it is unreachable.
"""
import os
import asyncio

import asyncpg
import pytest
from fastapi.testclient import TestClient

from hub.services.api.security import PAIRING_CODE

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
    from hub.services.api.main import app  # imported after DATABASE_URL is set

    with TestClient(app) as c:  # runs the app lifespan (DB pool + PG listener)
        yield c


def _pair(client) -> str:
    resp = client.post("/api/v1/pair", json={"pairing_code": PAIRING_CODE})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["token_type"] == "bearer"
    assert data["access_token"] and data["client_id"] and data["expires_at"]
    return data["access_token"]


def test_health_is_open(client):
    assert client.get("/health").status_code == 200


def test_nodes_requires_token(client):
    # No Authorization header -> 401 (the endpoint used to be fully open).
    resp = client.get("/api/v1/nodes")
    assert resp.status_code == 401


def test_pair_with_wrong_code_is_rejected(client):
    resp = client.post("/api/v1/pair", json={"pairing_code": PAIRING_CODE + "-wrong"})
    assert resp.status_code == 401


def test_pair_then_access_nodes(client):
    token = _pair(client)
    resp = client.get("/api/v1/nodes", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json()["data"], list)


def test_garbage_token_is_rejected(client):
    resp = client.get(
        "/api/v1/nodes", headers={"Authorization": "Bearer not.a.real.jwt"}
    )
    assert resp.status_code == 401


def test_events_also_protected(client):
    assert client.get("/api/v1/events").status_code == 401
    token = _pair(client)
    resp = client.get("/api/v1/events", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
