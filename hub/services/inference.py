import os
import json
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
import asyncpg
from typing import Dict, Any, List

# Ensure path to shared is importable
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Optional ONNX Runtime import
try:
    import onnxruntime as ort
except ImportError:
    ort = None

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/aurasense")
MODEL_REGISTRY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/registry.json"))
INFERENCE_INTERVAL_SEC = 15

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("inference-service")

class InferenceService:
    def __init__(self):
        self.db_pool = None
        self.models = {}
        self.load_model_registry()

    def load_model_registry(self):
        logger.info("Loading model registry...")
        if not os.path.exists(MODEL_REGISTRY_PATH):
            logger.error(f"Registry file not found at {MODEL_REGISTRY_PATH}")
            return
        
        with open(MODEL_REGISTRY_PATH, "r") as f:
            self.registry = json.load(f)
        
        for model_name, info in self.registry.items():
            model_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models", info["file"]))
            if ort and os.path.exists(model_file_path):
                try:
                    logger.info(f"Loading ONNX model {model_name} from {model_file_path}...")
                    self.models[model_name] = ort.InferenceSession(model_file_path)
                except Exception as e:
                    logger.error(f"Failed to load ONNX model {model_name}: {e}")
            else:
                logger.warning(f"ONNX model file {info['file']} not found or onnxruntime not installed. Using simulation mode for {model_name}.")

    async def connect_db(self):
        logger.info("Connecting to database...")
        self.db_pool = await asyncpg.create_pool(DATABASE_URL)
        logger.info("Connected to database.")

    async def run_nilm(self, conn, node_id: str):
        """
        NILM: Non-Intrusive Load Monitoring
        Pulls last 5 minutes of 'power' readings for the node.
        Disaggregates it into appliance usage.
        """
        # Pull last 5 min readings
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        rows = await conn.fetch(
            """
            SELECT ts, features FROM sensor_readings 
            WHERE node_id = $1 AND type = 'power' AND ts >= $2
            ORDER BY ts ASC
            """,
            node_id, cutoff
        )

        if not rows:
            return

        # Prepare input data
        power_values = []
        for r in rows:
            feats = json.loads(r["features"])
            # apparent_power is the key power indicator
            power_values.append(feats.get("apparent_power", 0.0))

        if not power_values:
            return

        avg_power = sum(power_values) / len(power_values)

        # Simulation or Real Model Execution
        if "nilm" in self.models:
            # Here we would do actual ONNX inference
            # inputs = {self.models["nilm"].get_inputs()[0].name: np.array([power_values], dtype=np.float32)}
            # outputs = self.models["nilm"].run(None, inputs)
            # disaggregated = parse_outputs(outputs)
            pass
        
        # Fallback simulation logic
        # If total apparent power is high, simulate appliances running
        fridge_w = 150.0 if avg_power > 150 else 20.0
        microwave_w = 1200.0 if avg_power > 1300 else 0.0
        hvac_w = 2000.0 if avg_power > 2200 else 0.0
        other_w = max(0.0, avg_power - (fridge_w + microwave_w + hvac_w))

        disaggregated_payload = {
            "refrigerator": fridge_w,
            "microwave": microwave_w,
            "hvac": hvac_w,
            "other": other_w
        }

        # Log an event if microwave is drawing excessive continuous power
        if microwave_w > 1000 and len(power_values) > 10:
            # Check if event already raised in the last 10 minutes
            existing = await conn.fetchval(
                """
                SELECT COUNT(*) FROM events 
                WHERE node_id = $1 AND type = 'microwave_running' AND ts >= $2
                """,
                node_id, datetime.now(timezone.utc) - timedelta(minutes=10)
            )
            if existing == 0:
                event_id = str(uuid.uuid4())
                await conn.execute(
                    """
                    INSERT INTO events (event_id, ts, type, severity, node_id, payload, acknowledged)
                    VALUES ($1, $2, 'microwave_running', 'INFO', $3, $4, FALSE)
                    """,
                    event_id, datetime.now(timezone.utc), node_id, json.dumps(disaggregated_payload)
                )
                logger.info(f"Raised microwave_running event for node {node_id}")

    async def run_fall_detection(self, conn, node_id: str):
        """
        Fall detection: runs on 'motion' readings (mmWave radar).
        """
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=30)
        rows = await conn.fetch(
            """
            SELECT ts, features FROM sensor_readings
            WHERE node_id = $1 AND type = 'motion' AND ts >= $2
            ORDER BY ts ASC
            """,
            node_id, cutoff
        )

        if not rows:
            return

        fall_triggered = False
        breathing_anomaly = False

        for r in rows:
            feats = json.loads(r["features"])
            if feats.get("fall_detected", False):
                fall_triggered = True
            
            breathing = feats.get("breathing_rate", 16.0)
            if breathing < 8.0 or breathing > 30.0:
                breathing_anomaly = True

        # Raise event if fall detected
        if fall_triggered:
            # Throttle alerts: only raise if no critical fall event in last 1 minute
            existing = await conn.fetchval(
                """
                SELECT COUNT(*) FROM events
                WHERE node_id = $1 AND type = 'fall_detected' AND ts >= $2
                """,
                node_id, datetime.now(timezone.utc) - timedelta(minutes=1)
            )
            if existing == 0:
                event_id = str(uuid.uuid4())
                await conn.execute(
                    """
                    INSERT INTO events (event_id, ts, type, severity, node_id, payload, acknowledged)
                    VALUES ($1, $2, 'fall_detected', 'CRITICAL', $3, $4, FALSE)
                    """,
                    event_id, datetime.now(timezone.utc), node_id, json.dumps({"description": "Elderly fall detected by mmWave sensor!"})
                )
                logger.critical(f"ALERT: Fall detected on node {node_id}")

    async def run_behavioral_anomaly(self, conn):
        """
        Runs anomaly detection across all nodes' features over the past hour.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Calculate behavioral stats
        # For simulation, compute average environment changes and motion activity
        row_count = await conn.fetchval(
            "SELECT COUNT(*) FROM sensor_readings WHERE ts >= $1", cutoff
        )

        if row_count == 0:
            return

        # Simple threshold-based behavioral score simulation
        # High activity at abnormal hours (e.g. 3 AM) yields high anomaly score
        current_hour = datetime.now(timezone.utc).hour
        score = 0.1
        context = {"total_readings_last_hour": row_count}

        if 1 <= current_hour <= 4:
            # Night time activity check
            motion_events = await conn.fetchval(
                "SELECT COUNT(*) FROM sensor_readings WHERE type = 'motion' AND ts >= $1", cutoff
            )
            if motion_events > 5:
                score = 0.85
                context["night_activity_count"] = motion_events
                context["description"] = "Unexpected high level of motion detected during sleeping hours."

        # Insert anomaly score
        await conn.execute(
            """
            INSERT INTO anomaly_scores (ts, model, score, context)
            VALUES ($1, 'behavioral_isolation_forest', $2, $3)
            """,
            datetime.now(timezone.utc), score, json.dumps(context)
        )

        # Raise event if high score
        if score > 0.80:
            existing = await conn.fetchval(
                """
                SELECT COUNT(*) FROM events
                WHERE type = 'behavioral_anomaly' AND ts >= $1
                """,
                datetime.now(timezone.utc) - timedelta(hours=1)
            )
            if existing == 0:
                # Find a node to blame or label system-wide
                node_id = await conn.fetchval("SELECT node_id FROM nodes LIMIT 1") or "system"
                event_id = str(uuid.uuid4())
                await conn.execute(
                    """
                    INSERT INTO events (event_id, ts, type, severity, node_id, payload, acknowledged)
                    VALUES ($1, $2, 'behavioral_anomaly', 'WARNING', $3, $4, FALSE)
                    """,
                    event_id, datetime.now(timezone.utc), node_id, json.dumps(context)
                )
                logger.warning(f"Raised behavioral anomaly event: {context}")

    async def execute_inference_cycle(self):
        async with self.db_pool.acquire() as conn:
            # Get list of online nodes
            nodes = await conn.fetch("SELECT node_id, type FROM nodes WHERE status = 'ONLINE'")
            
            for node in nodes:
                node_id = node["node_id"]
                node_type = node["type"]

                if node_type == "power":
                    await self.run_nilm(conn, node_id)
                elif node_type == "motion":
                    await self.run_fall_detection(conn, node_id)
            
            # Run global behavioral anomaly detector
            await self.run_behavioral_anomaly(conn)

    async def check_node_stale_status(self):
        """
        Updates node statuses to STALE / OFFLINE if last_seen is too old.
        """
        now_ts = int(datetime.now(timezone.utc).timestamp())
        async with self.db_pool.acquire() as conn:
            # Nodes not seen for 60s are STALE
            await conn.execute(
                "UPDATE nodes SET status = 'STALE' WHERE last_seen < $1 AND status = 'ONLINE'",
                now_ts - 60
            )
            # Nodes not seen for 300s are OFFLINE
            await conn.execute(
                "UPDATE nodes SET status = 'OFFLINE' WHERE last_seen < $1 AND status != 'OFFLINE'",
                now_ts - 300
            )

    async def run(self):
        await self.connect_db()
        logger.info("Starting background inference engine loop...")

        try:
            while True:
                start_time = asyncio.get_event_loop().time()
                try:
                    await self.execute_inference_cycle()
                    await self.check_node_stale_status()
                except Exception as e:
                    logger.error(f"Error in inference cycle: {e}", exc_info=True)
                
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0.1, INFERENCE_INTERVAL_SEC - elapsed)
                await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            logger.info("Inference service is shutting down...")
        finally:
            if self.db_pool:
                await self.db_pool.close()

if __name__ == "__main__":
    service = InferenceService()
    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:
        logger.info("Service stopped by user.")
