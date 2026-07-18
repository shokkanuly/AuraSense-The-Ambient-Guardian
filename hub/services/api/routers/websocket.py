import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncpg
import os

router = APIRouter()
logger = logging.getLogger("websocket-router")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/aurasense")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        # Broadcast message to all active WebSocket clients
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to socket: {e}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()

async def listen_for_events():
    """
    Subscribes to PG NOTIFY events on the 'events_channel'.
    Broadcasts any received notifications to active WebSockets.
    """
    logger.info("Initializing PG Listen/Notify listener for events...")
    while True:
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            
            def handle_notification(connection, pid, channel, payload):
                logger.info(f"PG Notification received on channel {channel}: {payload}")
                try:
                    payload_dict = json.loads(payload)
                    # Broadcast immediately to all active WS clients
                    asyncio.create_task(manager.broadcast({
                        "type": "event_notification",
                        "data": payload_dict
                    }))
                except Exception as e:
                    logger.error(f"Error processing notification payload: {e}")

            # Register listener
            await conn.add_listener("events_channel", handle_notification)
            logger.info("PG listener registered on 'events_channel'.")

            # Keep connection alive and listening
            while True:
                await asyncio.sleep(60)

        except (asyncio.CancelledError, GeneratorExit):
            logger.info("PG listener loop task cancelled.")
            break
        except Exception as e:
            logger.error(f"Database connection error in PG listener loop: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

# Start listener task as a background task upon importing/starting router
@router.on_event("startup")
async def start_websocket_listener():
    asyncio.create_task(listen_for_events())

@router.websocket("/ws/v1/events")
async def websocket_events_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Keep connection open. If client sends messages, we can handle them
        while True:
            data = await websocket.receive_text()
            # Respond to ping messages to keep socket alive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket execution error: {e}")
        manager.disconnect(websocket)
