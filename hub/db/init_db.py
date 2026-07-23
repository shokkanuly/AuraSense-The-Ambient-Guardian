"""Initialize the AuraSense database schema (idempotent).

Applies ``hub/db/schema.sql`` to ``DATABASE_URL``. Used by CI against a fresh
Postgres service container, and usable locally against the docker-compose DB.
The schema uses IF NOT EXISTS / OR REPLACE throughout, so re-running is safe.
"""
import asyncio
import os

import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/aurasense"
)
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


async def main() -> None:
    with open(SCHEMA_PATH) as f:
        sql = f.read()
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(sql)
        print(f"Applied schema from {SCHEMA_PATH} to {DATABASE_URL}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
