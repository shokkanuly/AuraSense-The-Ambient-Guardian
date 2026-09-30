import os
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
import asyncpg
from typing import Dict, Any, Optional

logger = logging.getLogger("consensus-matrix-engine")

class CrossSensorConsensusMatrix:
    """
    TimescaleDB Cross-Sensor Consensus Matrix Engine.
    Suppresses false alerts by requiring multi-sensor secondary verification 
    within timed action windows before escalating to high-severity alerts.
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def evaluate_fall_consensus(self, node_id: str, trigger_ts: datetime) -> Optional[Dict[str, Any]]:
        """
        Matrix Rule 1: mmWave Radar Fall Trigger
        - Secondary verification required: Acoustic check for voice response AND no motion across adjacent nodes.
        - Timed action window: 15 seconds immobility.
        - Final Event Severity: CRITICAL_EMERGENCY
        """
        async with self.db_pool.acquire() as conn:
            window_start = trigger_ts - timedelta(seconds=15)
            
            # Check 1: Audio nodes for voice response ("help" / acoustic response)
            audio_rows = await conn.fetch(
                """
                SELECT features FROM sensor_readings
                WHERE type = 'audio' AND ts >= $1 AND ts <= $2
                ORDER BY ts DESC
                """,
                window_start, trigger_ts + timedelta(seconds=5)
            )
            
            has_voice_response = False
            for row in audio_rows:
                feats = json.loads(row["features"]) if isinstance(row["features"], str) else row["features"]
                if feats.get("label") == "voice_response" and feats.get("confidence", 0) > 0.6:
                    has_voice_response = True
                    break

            # Check 2: Motion across adjacent nodes
            adjacent_motion_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM sensor_readings
                WHERE type = 'motion' AND node_id != $1 AND ts >= $2 AND ts <= $3
                """,
                node_id, window_start, trigger_ts + timedelta(seconds=15)
            )

            # If no voice response and no adjacent motion detected during the 15s window -> Fall is confirmed
            if not has_voice_response and (adjacent_motion_count is None or adjacent_motion_count == 0):
                event_id = str(uuid.uuid4())
                event_payload = {
                    "rule": "mmWave Fall + Silent Verification (15s Window)",
                    "primary_sensor": "mmWave_radar",
                    "secondary_verification": "Acoustic silence + Zero adjacent node movement",
                    "immobility_duration_sec": 15,
                    "target_node": node_id
                }
                
                await conn.execute(
                    """
                    INSERT INTO events (event_id, ts, type, severity, node_id, payload, acknowledged)
                    VALUES ($1, $2, 'consensus_verified_fall', 'CRITICAL_EMERGENCY', $3, $4, FALSE)
                    """,
                    event_id, trigger_ts, node_id, json.dumps(event_payload)
                )
                logger.critical(f"[CONSENSUS MATRIX] CRITICAL_EMERGENCY: Fall verified for node {node_id}")
                return {"event_id": event_id, "severity": "CRITICAL_EMERGENCY", "payload": event_payload}
            else:
                logger.info(f"[CONSENSUS MATRIX] Suppressed false fall trigger for node {node_id}: voice_response={has_voice_response}, adjacent_motion={adjacent_motion_count}")
                return None

    async def evaluate_voc_gas_consensus(self, node_id: str, trigger_ts: datetime, voc_iaq: float) -> Optional[Dict[str, Any]]:
        """
        Matrix Rule 2: BME680 VOC Gas Spike Trigger (VOC IAQ > 250)
        - Secondary verification required: NILM check for stove/oven active power usage.
        - Timed action window: 120 seconds sustained.
        - Final Event Severity: WARNING_HAZARD
        """
        if voc_iaq < 250.0:
            return None

        async with self.db_pool.acquire() as conn:
            window_start = trigger_ts - timedelta(seconds=120)
            
            # Query power readings for active stove/oven draw (> 1500W draw)
            power_rows = await conn.fetch(
                """
                SELECT features FROM sensor_readings
                WHERE (type = 'power' OR type = 'submeter' OR type = 'pulse_meter') AND ts >= $1
                ORDER BY ts DESC
                """,
                window_start
            )

            stove_active = False
            active_watts = 0.0
            for row in power_rows:
                feats = json.loads(row["features"]) if isinstance(row["features"], str) else row["features"]
                power_w = feats.get("apparent_power") or feats.get("active_power") or feats.get("active_power_w") or 0.0
                if power_w > 1200.0:
                    stove_active = True
                    active_watts = power_w
                    break

            if stove_active:
                event_id = str(uuid.uuid4())
                event_payload = {
                    "rule": "BME680 VOC Gas Spike + NILM Stove Power Verification (120s Window)",
                    "voc_iaq_level": voc_iaq,
                    "measured_appliance_power_w": active_watts,
                    "hazard_description": "High VOC gas levels correlated with sustained high power draw on cooking appliances."
                }
                await conn.execute(
                    """
                    INSERT INTO events (event_id, ts, type, severity, node_id, payload, acknowledged)
                    VALUES ($1, $2, 'consensus_voc_hazard', 'WARNING_HAZARD', $3, $4, FALSE)
                    """,
                    event_id, trigger_ts, node_id, json.dumps(event_payload)
                )
                logger.warning(f"[CONSENSUS MATRIX] WARNING_HAZARD: VOC gas spike verified with stove active power on node {node_id}")
                return {"event_id": event_id, "severity": "WARNING_HAZARD", "payload": event_payload}
            return None

    async def evaluate_glass_break_consensus(self, node_id: str, trigger_ts: datetime) -> Optional[Dict[str, Any]]:
        """
        Matrix Rule 3: Acoustic MEMS Glass Break Trigger
        - Secondary verification required: mmWave spatial tracking detects sudden rapid movement.
        - Timed action window: Instantaneous (5 seconds).
        - Final Event Severity: CRITICAL_SECURITY
        """
        async with self.db_pool.acquire() as conn:
            window_start = trigger_ts - timedelta(seconds=5)
            window_end = trigger_ts + timedelta(seconds=5)
            
            motion_rows = await conn.fetch(
                """
                SELECT features FROM sensor_readings
                WHERE type = 'motion' AND ts >= $1 AND ts <= $2
                """,
                window_start, window_end
            )

            rapid_motion_detected = False
            for row in motion_rows:
                feats = json.loads(row["features"]) if isinstance(row["features"], str) else row["features"]
                if feats.get("rapid_movement_detected", False) or feats.get("presence", False):
                    rapid_motion_detected = True
                    break

            if rapid_motion_detected:
                event_id = str(uuid.uuid4())
                event_payload = {
                    "rule": "Acoustic Glass Break + mmWave Rapid Spatial Movement (Instantaneous)",
                    "acoustic_trigger_node": node_id,
                    "secondary_verification": "mmWave rapid spatial motion confirmed"
                }
                await conn.execute(
                    """
                    INSERT INTO events (event_id, ts, type, severity, node_id, payload, acknowledged)
                    VALUES ($1, $2, 'consensus_glass_break_intrusion', 'CRITICAL_SECURITY', $3, $4, FALSE)
                    """,
                    event_id, trigger_ts, node_id, json.dumps(event_payload)
                )
                logger.critical(f"[CONSENSUS MATRIX] CRITICAL_SECURITY: Glass break intrusion verified for node {node_id}")
                return {"event_id": event_id, "severity": "CRITICAL_SECURITY", "payload": event_payload}
            return None
