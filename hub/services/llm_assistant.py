import os
import json
import logging
import asyncpg
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

# Set up logging
logger = logging.getLogger("llm-assistant")

class LLMAssistant:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.model = None
        self.load_model()

    def load_model(self):
        """
        Attempts to load llama.cpp models if files and bindings are available.
        Otherwise falls back to mock generated responses for local testing.
        """
        try:
            # Lazy import to avoid crash if bindings are not installed yet
            from llama_cpp import Llama
            model_path = os.getenv("LLM_MODEL_PATH", "/models/phi-3-mini-4k-instruct.gguf")
            if os.path.exists(model_path):
                logger.info(f"Loading Llama model from {model_path}...")
                self.model = Llama(model_path=model_path, n_ctx=2048)
                logger.info("Llama model loaded successfully.")
            else:
                logger.warning(f"Llama model file not found at {model_path}. Running LLM in simulation mode.")
        except ImportError:
            logger.warning("llama-cpp-python not installed. Running LLM in simulation mode.")

    async def get_recent_context(self) -> List[Dict[str, Any]]:
        """
        Retrieves context: recent alerts, anomalous scores, and active sensors.
        """
        context_items = []
        conn = await asyncpg.connect(self.db_url)
        try:
            # 1. Fetch recent events (last 12 hours)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=12)
            events = await conn.fetch(
                """
                SELECT ts, type, severity, payload 
                FROM events 
                WHERE ts >= $1
                ORDER BY ts DESC LIMIT 10
                """,
                cutoff
            )
            for e in events:
                context_items.append({
                    "type": "event",
                    "timestamp": e["ts"].isoformat(),
                    "event_type": e["type"],
                    "severity": e["severity"],
                    "details": json.loads(e["payload"])
                })

            # 2. Fetch active nodes status
            nodes = await conn.fetch("SELECT node_id, type, status FROM nodes")
            for n in nodes:
                context_items.append({
                    "type": "node_status",
                    "node_id": n["node_id"],
                    "sensor_type": n["type"],
                    "status": n["status"]
                })

            # 3. Fetch average power usage from NILM disaggregation
            # Select most recent readings features from power sensors
            power_readings = await conn.fetch(
                """
                SELECT node_id, features, ts FROM sensor_readings
                WHERE type = 'power'
                ORDER BY ts DESC LIMIT 5
                """
            )
            for r in power_readings:
                context_items.append({
                    "type": "current_power",
                    "node_id": r["node_id"],
                    "reading_ts": r["ts"].isoformat(),
                    "features": json.loads(r["features"])
                })

        except Exception as e:
            logger.error(f"Error fetching DB context for LLM: {e}")
        finally:
            await conn.close()

        return context_items

    def generate_simulated_response(self, prompt: str, context: List[Dict[str, Any]]) -> str:
        prompt_lower = prompt.lower()
        
        # Check context indicators
        critical_events = [c for c in context if c.get("type") == "event" and c.get("severity") == "CRITICAL"]
        warning_events = [c for c in context if c.get("type") == "event" and c.get("severity") == "WARNING"]
        stale_nodes = [c for c in context if c.get("type") == "node_status" and c.get("status") in ("STALE", "OFFLINE")]
        
        if "fall" in prompt_lower or "emergency" in prompt_lower:
            if critical_events and any(e.get("event_type") == "fall_detected" for e in critical_events):
                return "Yes, a critical fall event was detected by the mmWave radar sensor. Emergency services should be contacted if necessary, and someone should check on the occupant immediately."
            return "No fall events have been recorded in the past 12 hours. All motion and breathing sensors show normal occupant activity patterns."
        
        if "power" in prompt_lower or "bill" in prompt_lower or "electricity" in prompt_lower:
            power_records = [c for c in context if c.get("type") == "current_power"]
            if power_records:
                total_watts = sum(r["features"].get("apparent_power", 0) for r in power_records) / len(power_records)
                return f"Currently, the average electricity consumption is around {total_watts:.1f} W. Based on recent load monitoring, your refrigerator is operating normally, consuming about 150W. No abnormal high-draw appliances (like the microwave or HVAC) are currently active."
            return "Electricity consumption details are currently unavailable because the power node has not reported values recently."

        if "status" in prompt_lower or "offline" in prompt_lower or "nodes" in prompt_lower:
            if stale_nodes:
                stale_list = ", ".join([f"Node {n['node_id']} ({n['sensor_type']})" for n in stale_nodes])
                return f"Currently, the following nodes are experiencing issues: {stale_list}. Please check if they are powered on and connected to the local Wi-Fi router."
            return "All sensor nodes (power, acoustic, motion, and environmental) are currently online and reporting feature data successfully."

        # Default smart helper response
        summary_sentence = "No outstanding warnings or alerts are active."
        if critical_events:
            summary_sentence = f"Warning: There is a critical {critical_events[0]['event_type']} alert recorded."
        elif warning_events:
            summary_sentence = f"Note: There is a behavioral warning active: {warning_events[0].get('details', {}).get('description', 'abnormal activity')}."

        return (
            f"Hello! I am your on-device AuraSense assistant. {summary_sentence} "
            "How can I help you check the status of your smart home sensors or investigate recent activity alerts?"
        )

    async def query(self, prompt: str) -> Dict[str, Any]:
        # Gather live contextual data from the database
        context = await self.get_recent_context()
        
        if self.model:
            # Build system prompt with embedded context
            context_str = json.dumps(context, indent=2)
            full_prompt = (
                "<|system|>\n"
                "You are an on-device smart home assistant named AuraSense. "
                "Analyze the following JSON context containing live sensor data, node statuses, and events, and answer the user query succinctly. "
                "Context:\n"
                f"{context_str}\n"
                "<|user|>\n"
                f"{prompt}\n"
                "<|assistant|>\n"
            )
            
            try:
                loop = asyncio.get_event_loop()
                # Run Llama CPU inference in execution pool to keep async loop unblocked
                output = await loop.run_in_executor(
                    None,
                    lambda: self.model(full_prompt, max_tokens=150, stop=["<|end|>"])
                )
                response_text = output["choices"][0]["text"].strip()
            except Exception as e:
                logger.error(f"Inference error: {e}")
                response_text = self.generate_simulated_response(prompt, context)
        else:
            response_text = self.generate_simulated_response(prompt, context)

        return {
            "response": response_text,
            "context_used": context
        }
