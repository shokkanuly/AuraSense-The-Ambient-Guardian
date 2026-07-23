"""
F3 verification — the device simulator produces payloads that are valid against
the shared sensor contracts, and each scenario perturbs the right sensor.

Pure/offline: no DB or MQTT broker required.
"""
import random

import pytest

from shared.types.sensor_payload import PAYLOAD_MODELS
from tools.sim.generator import FLEET, SCENARIOS, build_payload


@pytest.mark.parametrize("sensor_type", sorted(set(FLEET.values())))
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_generated_payload_validates_against_contract(sensor_type, scenario):
    rng = random.Random(1234)  # deterministic
    payload = build_payload(sensor_type, scenario, ts=1_700_000_000, rng=rng)
    # Ingestion injects node_id/type from the topic before validating; mirror that.
    payload = {**payload, "node_id": "node_x", "type": sensor_type}
    model = PAYLOAD_MODELS[sensor_type]
    validated = model(**payload)  # raises ValidationError on any contract mismatch
    assert validated.type == sensor_type


def test_fall_scenario_sets_fall_detected():
    feats = build_payload("motion", "fall", rng=random.Random(1))["features"]
    assert feats["fall_detected"] is True and feats["presence"] is True


def test_microwave_scenario_draws_high_power():
    # NILM microwave_running fires above ~1.3 kVA; the scenario must exceed it.
    feats = build_payload("power", "microwave", rng=random.Random(1))["features"]
    assert feats["apparent_power"] > 1300


def test_water_scenario_labels_running_water():
    feats = build_payload("audio", "water", rng=random.Random(1))["features"]
    assert feats["label"] == "running_water"


def test_unknown_inputs_raise():
    with pytest.raises(ValueError):
        build_payload("power", "nonsense-scenario")
    with pytest.raises(ValueError):
        build_payload("nonsense-sensor", "normal")
