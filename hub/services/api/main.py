import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

# CORS: permissive for local development. Stage F2 replaces this with an
# allow-list of the dashboard/app origins once pairing-based auth lands.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db(request: Request):
    async with request.app.state.db_pool.acquire() as conn:
        yield conn


# Simple Authentication placeholder — replaced by real pairing-token auth in F2.
security = HTTPBearer(auto_error=False)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # In full production (F2), decode the JWT minted from the local pairing secret.
    # For now, validate presence only.
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "AuraSense Hub API"}


# Import and include routers (imported last: they depend on get_db defined above)
from hub.services.api.routers import nodes, events, assistant, websocket

app.include_router(nodes.router, prefix="/api/v1", tags=["Nodes"])
app.include_router(events.router, prefix="/api/v1", tags=["Events"])
app.include_router(assistant.router, prefix="/api/v1", tags=["Assistant"])
app.include_router(websocket.router, tags=["WebSockets"])
