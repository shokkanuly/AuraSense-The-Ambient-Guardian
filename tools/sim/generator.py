"""Sensor payload generator for the AuraSense device simulator.

Pure functions (no MQTT, no DB, no shared-type imports) that produce feature
dicts matching ``shared/types/sensor_payload.py``. Kept dependency-free so they
are trivially unit-testable and so the generated payloads can be validated
against the Pydantic contracts in a test.

Scenarios perturb one sensor toward an event the hub should detect:
  * ``fall``      -> motion node reports ``fall_detected`` (CRITICAL)
  * ``microwave`` -> power node draws >1.3 kVA (NILM microwave_running, INFO)
  * ``water``     -> acoustic node reports ``running_water``
  * ``night``     -> extra motion (behavioral anomaly, if run during 1-4am local)
  * ``normal``    -> quiet baseline
"""
from __future__ import annotations

import random
import time
from typing import Any, Dict, Optional

SCENARIOS = ("normal", "fall", "microwave", "water", "night")

# node_id -> sensor_type. Matches the dashboard's demo fleet for continuity.
FLEET: Dict[str, str] = {
    "node_power_01": "power",
    "node_acoustic_02": "audio",
    "node_presence_03": "motion",
    "node_env_04": "env",
}


def power_features(scenario: str, rng: random.Random) -> Dict[str, Any]:
    voltage = round(rng.uniform(118.0, 122.0), 2)
    if scenario == "microwave":
        current = round(rng.uniform(11.5, 13.0), 2)  # ~1.4-1.6 kVA
    else:
        base = rng.uniform(1.5, 2.4)  # fridge / base load
        if rng.random() < 0.2:
            base += rng.uniform(0.6, 1.0)  # compressor kick
        current = round(base, 2)
    return {
        "rms_current": current,
        "rms_voltage": voltage,
        "apparent_power": round(voltage * current, 2),
        "thd": round(rng.uniform(0.02, 0.08), 3),
    }


def audio_features(scenario: str, rng: random.Random) -> Dict[str, Any]:
    if scenario == "water":
        return {"label": "running_water", "confidence": round(rng.uniform(0.85, 0.98), 3)}
    return {"label": "none", "confidence": round(rng.uniform(0.0, 0.15), 3)}


def motion_features(scenario: str, rng: random.Random) -> Dict[str, Any]:
    point_cloud = [round(rng.uniform(-1.0, 1.0), 3) for _ in range(4)]
    if scenario == "fall":
        return {
            "presence": True,
            "breathing_rate": round(rng.uniform(9.0, 14.0), 1),
            "fall_detected": True,
            "point_cloud_summary": point_cloud,
        }
    presence = rng.random() < (0.85 if scenario == "night" else 0.6)
    return {
        "presence": presence,
        "breathing_rate": round(rng.uniform(12.0, 18.0), 1),
        "fall_detected": False,
        "point_cloud_summary": point_cloud,
    }


def env_features(scenario: str, rng: random.Random) -> Dict[str, Any]:
    return {
        "temp_c": round(rng.uniform(20.0, 23.5), 2),
        "humidity_pct": round(rng.uniform(40.0, 55.0), 1),
        "pressure_hpa": round(rng.uniform(1000.0, 1015.0), 1),
        "voc_iaq": round(rng.uniform(50.0, 120.0), 1),
    }


_GENERATORS = {
    "power": power_features,
    "audio": audio_features,
    "motion": motion_features,
    "env": env_features,
}


def build_payload(
    sensor_type: str,
    scenario: str = "normal",
    ts: Optional[int] = None,
    rng: Optional[random.Random] = None,
) -> Dict[str, Any]:
    """Build a full MQTT payload dict (``{"ts": ..., "features": {...}}``)."""
    if sensor_type not in _GENERATORS:
        raise ValueError(f"unknown sensor_type: {sensor_type}")
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario}")
    r = rng if rng is not None else random
    return {
        "ts": int(ts if ts is not None else time.time()),
        "features": _GENERATORS[sensor_type](scenario, r),
    }
