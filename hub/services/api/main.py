import os
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncpg

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("api-service")

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/aurasense")

# FastAPI App initialization
app = FastAPI(
    title="AuraSense Hub API",
    description="Privacy-first Local Smart Home IoT and Edge AI REST / WebSocket API",
    version="1.0.0"
)

# Enable CORS for Next.js dashboard and external local clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB Pool dependency
db_pool = None

@app.on_event("startup")
async def startup():
    global db_pool
    logger.info("Initializing database pool for API...")
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    logger.info("Database pool initialized.")

@app.on_event("shutdown")
async def shutdown():
    global db_pool
    if db_pool:
        logger.info("Closing database pool...")
        await db_pool.close()
        logger.info("Database pool closed.")

async def get_db():
    async with db_pool.acquire() as conn:
        yield conn

# Simple Authentication placeholder
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # In full production, decode JWT local pairing secrets.
    # For now, validate presence.
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "AuraSense Hub API"}

# Import and include routers (we will create these next)
from hub.services.api.routers import nodes, events, assistant, websocket

app.include_router(nodes.router, prefix="/api/v1", tags=["Nodes"])
app.include_router(events.router, prefix="/api/v1", tags=["Events"])
app.include_router(assistant.router, prefix="/api/v1", tags=["Assistant"])
app.include_router(websocket.router, tags=["WebSockets"])
