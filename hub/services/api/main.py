import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
import asyncpg

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("api-service")

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/aurasense")

# Imported here (top-level) so the lifespan can start the event bridge and the
# assistant. Neither module imports back into this one, so there is no cycle.
from hub.services.api.routers.websocket import listen_for_events
from hub.services.llm_assistant import LLMAssistant
from hub.services.api.security import verify_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: owns the DB pool, the on-device assistant, and the
    Postgres LISTEN/NOTIFY -> WebSocket bridge.

    The bridge previously lived on a router ``startup`` hook, which FastAPI does
    not run — so live events were never broadcast. Starting it here fixes that.
    """
    logger.info("Initializing database pool for API...")
    app.state.db_pool = await asyncpg.create_pool(DATABASE_URL)
    logger.info("Database pool initialized.")

    # The assistant shares the pool. Load the (optional) local LLM off the event
    # loop so a missing/large model file never blocks API startup.
    app.state.assistant = LLMAssistant(app.state.db_pool)
    app.state.assistant_load_task = asyncio.create_task(
        asyncio.to_thread(app.state.assistant.load_model)
    )

    # Start the events bridge at the app level so it actually runs.
    app.state.event_listener_task = asyncio.create_task(listen_for_events())

    try:
        yield
    finally:
        logger.info("Shutting down API services...")
        for task_name in ("event_listener_task", "assistant_load_task"):
            task = getattr(app.state, task_name, None)
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        if app.state.db_pool:
            await app.state.db_pool.close()
            logger.info("Database pool closed.")


# FastAPI App initialization
app = FastAPI(
    title="AuraSense Hub API",
    description="Privacy-first Local Smart Home IoT and Edge AI REST / WebSocket API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS restricted to the configured dashboard/app origins. Note that a wildcard
# origin combined with credentials is rejected by browsers anyway, so this is
# both safer and more correct. Override with AURASENSE_ALLOWED_ORIGINS (CSV).
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "AURASENSE_ALLOWED_ORIGINS",
        # Dashboard dev server (Vite) runs on :8080; :3000 kept as a common default.
        "http://localhost:8080,http://localhost:3000",
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db(request: Request):
    async with request.app.state.db_pool.acquire() as conn:
        yield conn


# Health check endpoint (open — used for liveness probes)
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "AuraSense Hub API"}


# Import and include routers (imported last: they depend on get_db defined above).
# The data routers require a valid pairing token; /pair and the health check are open.
from hub.services.api.routers import nodes, events, assistant, websocket, pairing, energy

app.include_router(pairing.router, prefix="/api/v1", tags=["Pairing"])
app.include_router(nodes.router, prefix="/api/v1", tags=["Nodes"], dependencies=[Depends(verify_token)])
app.include_router(events.router, prefix="/api/v1", tags=["Events"], dependencies=[Depends(verify_token)])
app.include_router(assistant.router, prefix="/api/v1", tags=["Assistant"], dependencies=[Depends(verify_token)])
app.include_router(energy.router, prefix="/api/v1", tags=["Data"], dependencies=[Depends(verify_token)])
app.include_router(websocket.router, tags=["WebSockets"])
