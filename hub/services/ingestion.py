import os
import json
import asyncio
import logging
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
import asyncpg
from pydantic import ValidationError

# Ensure path to shared is importable
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from shared.types.sensor_payload import PAYLOAD_MODELS

# Configuration
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/aurasense")

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ingestion-service")


class IngestionService:
    def __init__(self):
        self.db_pool = None
        self.loop = None
        self.queue = None

    async def connect_db(self):
        logger.info("Connecting to database...")
        self.db_pool = await asyncpg.create_pool(DATABASE_URL)
        logger.info("Connected to database.")

    async def process_queue(self):
        logger.info("Starting database ingestion worker queue processing...")
        while True:
            msg = await self.queue.get()
            try:
                await self.ingest_message(msg)
            except Exception as e:
                logger.error(f"Error ingesting message: {e}", exc_info=True)
            finally:
                self.queue.task_done()

    async def ingest_message(self, msg: dict):
        topic = msg["topic"]
        payload_str = msg["payload"]

        # Parse topic: aurasense/nodes/{node_id}/{sensor_type}
        parts = topic.split('/')
        if len(parts) < 4:
            logger.warning(f"Invalid topic format: {topic}")
            return

        node_id = parts[2]
        sensor_type = parts[3]

        if sensor_type not in PAYLOAD_MODELS:
            logger.warning(f"Unknown sensor type: {sensor_type}")
            return

        try:
            payload_data = json.loads(payload_str)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON payload on topic {topic}")
            return

        # Inject topic fields if missing to validate complete Pydantic models
        if "node_id" not in payload_data:
            payload_data["node_id"] = node_id
        if "type" not in payload_data:
            payload_data["type"] = sensor_type

        # Validate payload
        try:
            model = PAYLOAD_MODELS[sensor_type]
            validated = model(**payload_data)
        except ValidationError as ve:
            logger.error(f"Validation failed for sensor {sensor_type} on node {node_id}: {ve}")
            return

        ts_datetime = datetime.fromtimestamp(validated.ts, tz=timezone.utc)

        # Write to Database
        async with self.db_pool.acquire() as conn:
            # 1. Update/Upsert the Node registry
            await conn.execute(
                """
                INSERT INTO nodes (node_id, type, last_seen, firmware_version, status)
                VALUES ($1, $2, $3, $4, 'ONLINE')
                ON CONFLICT (node_id)
                DO UPDATE SET last_seen = EXCLUDED.last_seen, status = 'ONLINE'
                """,
                validated.node_id,
                validated.type,
                validated.ts,
                payload_data.get("firmware_version", "1.0.0")
            )

            # 2. Insert the actual readings hypertable entry
            await conn.execute(
                """
                INSERT INTO sensor_readings (ts, node_id, type, features)
                VALUES ($1, $2, $3, $4)
                """,
                ts_datetime,
                validated.node_id,
                validated.type,
                json.dumps(validated.features.model_dump())
            )

        logger.info(f"Ingested {sensor_type} reading for node {node_id} at ts {validated.ts}")

    def on_mqtt_message(self, client, userdata, message):
        payload_str = message.payload.decode("utf-8")
        data = {
            "topic": message.topic,
            "payload": payload_str
        }
        # Safely submit to the asyncio event loop queue
        self.loop.call_soon_threadsafe(self.queue.put_nowait, data)

    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        # paho-mqtt v2 (CallbackAPIVersion.VERSION2) signature. ``reason_code``
        # compares equal to 0 on success.
        if reason_code == 0:
            logger.info("Connected to MQTT Broker!")
            # Subscribe to all sensor node readings
            client.subscribe("aurasense/nodes/#")
        else:
            logger.error(f"Failed to connect to MQTT Broker, reason code {reason_code}")

    async def run(self):
        self.loop = asyncio.get_running_loop()
        self.queue = asyncio.Queue()
        await self.connect_db()

        # Start database insertion worker
        asyncio.create_task(self.process_queue())

        # Setup MQTT Client (paho-mqtt v2 callback API)
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = self.on_mqtt_connect
        client.on_message = self.on_mqtt_message

        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_start()
            logger.info(f"MQTT Client loop started, broker={MQTT_BROKER}:{MQTT_PORT}")
            
            # Keep running indefinitely
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("Ingestion service is shutting down...")
        finally:
            client.loop_stop()
            if self.db_pool:
                await self.db_pool.close()

if __name__ == "__main__":
    service = IngestionService()
    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:
        logger.info("Service stopped by user.")
