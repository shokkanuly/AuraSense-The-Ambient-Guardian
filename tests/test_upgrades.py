import unittest
import asyncio
from datetime import datetime, timezone
from shared.types.sensor_payload import (
    SubmeterPayload, OpticalPulsePayload, AudioPayload, MotionPayload, EnvPayload
)
from shared.types.ml_contracts import NILMInput, NILMOutput
from shared.types.api_types import EventPayload

class TestAuraSenseUpgrades(unittest.TestCase):

    def test_submeter_payload_validation(self):
        payload = SubmeterPayload(
            node_id="submeter_plug_01",
            ts=1720000000,
            features={
                "appliance_id": "heat_pump",
                "active_power": 2150.5,
                "voltage": 230.0,
                "current": 9.35
            }
        )
        self.assertEqual(payload.type, "submeter")
        self.assertEqual(payload.features.appliance_id, "heat_pump")
        self.assertEqual(payload.features.active_power, 2150.5)

    def test_optical_pulse_payload_validation(self):
        payload = OpticalPulsePayload(
            node_id="optical_pulse_node_01",
            ts=1720000000,
            features={
                "pulse_count": 14500,
                "imp_per_kwh": 1000,
                "active_power_w": 1850.0
            }
        )
        self.assertEqual(payload.type, "pulse_meter")
        self.assertEqual(payload.features.pulse_count, 14500)
        self.assertEqual(payload.features.active_power_w, 1850.0)

    def test_motion_occlusion_and_rapid_movement_fields(self):
        motion = MotionPayload(
            node_id="motion_node_01",
            ts=1720000000,
            features={
                "presence": True,
                "breathing_rate": 16.0,
                "fall_detected": True,
                "stationary_reflection_ratio": 0.98,
                "rapid_movement_detected": True,
                "point_cloud_summary": [0.1, 0.5, 0.9]
            }
        )
        self.assertTrue(motion.features.fall_detected)
        self.assertEqual(motion.features.stationary_reflection_ratio, 0.98)
        self.assertTrue(motion.features.rapid_movement_detected)

    def test_ml_contracts_submeter_anchors(self):
        nilm_in = NILMInput(
            power_sequence=[[230.0, 10.0, 2300.0, 0.05]],
            submeter_anchors={"heat_pump": 2100.0}
        )
        self.assertEqual(nilm_in.submeter_anchors["heat_pump"], 2100.0)

        nilm_out = NILMOutput(
            appliance_power={"heat_pump": 2100.0, "fridge": 150.0},
            calibration_anchors_applied=["heat_pump"]
        )
        self.assertIn("heat_pump", nilm_out.calibration_anchors_applied)

    def test_event_payload_severity_tiers(self):
        ev = EventPayload(
            event_id="evt_123",
            ts=1720000000,
            type="consensus_verified_fall",
            severity="CRITICAL_EMERGENCY",
            node_id="motion_node_01",
            payload={"verified": True},
            acknowledged=False
        )
        self.assertEqual(ev.severity, "CRITICAL_EMERGENCY")

    def test_optical_pulse_power_calculation(self):
        # 1000 imp/kWh, diff between pulses = 200,000 microseconds (0.2s)
        # Power (W) = 3,600,000,000 / (1000 * 200000) = 18.0 W
        imp_per_kwh = 1000
        diff_us = 200000
        power_w = 3600000000.0 / (imp_per_kwh * diff_us)
        self.assertAlmostEqual(power_w, 18.0)

    def test_llm_assistant_simulated_response(self):
        from hub.services.llm_assistant import LLMAssistant
        assistant = LLMAssistant(db_url="postgresql://fake:fake@localhost:5432/fake")
        
        mock_context = [
            {
                "type": "event",
                "event_type": "high_appliance_draw",
                "severity": "INFO",
                "details": {"description": "sustained high draw"}
            },
            {
                "type": "submeter_anchor",
                "ev_charger": 3500.0
            }
        ]
        response = assistant.generate_simulated_response("Why was my bill high on Tuesday?", mock_context)
        self.assertIn("Tuesday", response)
        self.assertIn("NILM", response)

if __name__ == "__main__":
    unittest.main()

