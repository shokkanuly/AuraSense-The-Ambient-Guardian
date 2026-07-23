"""AuraSense device simulator CLI.

Publishes schema-valid sensor feature vectors to the local MQTT broker so the
hub pipeline (ingestion -> inference -> events -> API/WS) can be exercised
without physical nodes.

Examples:
    python -m tools.sim --scenario normal
    python -m tools.sim --scenario fall --duration 10
    python -m tools.sim --scenario microwave --rounds 15 --interval 1
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from typing import Optional, Sequence

import paho.mqtt.client as mqtt

from tools.sim.generator import FLEET, SCENARIOS, build_payload

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - sim - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sim")


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="tools.sim", description="AuraSense device simulator")
    p.add_argument("--scenario", choices=SCENARIOS, default="normal")
    p.add_argument("--broker", default="localhost")
    p.add_argument("--port", type=int, default=1883)
    p.add_argument("--interval", type=float, default=2.0, help="seconds between rounds")
    p.add_argument("--duration", type=float, default=None, help="stop after N seconds")
    p.add_argument("--rounds", type=int, default=None, help="stop after N rounds")
    args = p.parse_args(argv)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(args.broker, args.port, 60)
    client.loop_start()
    logger.info(
        "publishing scenario=%s to %s:%s (fleet of %d nodes)",
        args.scenario, args.broker, args.port, len(FLEET),
    )

    start = time.time()
    rounds = 0
    try:
        while True:
            for node_id, sensor_type in FLEET.items():
                payload = build_payload(sensor_type, args.scenario)
                topic = f"aurasense/nodes/{node_id}/{sensor_type}"
                client.publish(topic, json.dumps(payload), qos=0)
            rounds += 1
            logger.info("round %d published", rounds)

            if args.rounds is not None and rounds >= args.rounds:
                break
            if args.duration is not None and (time.time() - start) >= args.duration:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("stopped by user")
    finally:
        client.loop_stop()
        client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
