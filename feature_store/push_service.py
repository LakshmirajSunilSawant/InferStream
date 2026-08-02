"""
InferStream — Feast Push Service.

Consumes the Kafka `computed-features` topic (produced by the Flink job) and
pushes each record into the Feast online store via the PushSource. This is the
canonical writer for the Feast-served online features; the API reads them back
with feast_client.get_online_features(). Decoupling the push here keeps the
heavy Feast dependency out of the Flink (PyFlink/JVM) container.
"""
import os
import json
import time
import signal
import logging

from kafka import KafkaConsumer

import feast_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_FEATURES  = os.getenv("KAFKA_TOPIC_FEATURES",    "computed-features")

_running = True


def _handle_signal(signum, frame):
    global _running
    logger.info(f"🛑 Received signal {signum} — stopping push service...")
    _running = False


def connect_consumer(max_retries: int = 15) -> KafkaConsumer:
    for i in range(max_retries):
        try:
            consumer = KafkaConsumer(
                TOPIC_FEATURES,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id="feast-push-service",
                auto_offset_reset="latest",
                enable_auto_commit=True,
                value_deserializer=lambda b: json.loads(b.decode("utf-8")),
            )
            logger.info(f"✅ Subscribed to Kafka topic: {TOPIC_FEATURES}")
            return consumer
        except Exception as e:
            logger.warning(f"Kafka not ready ({i+1}/{max_retries}): {e}")
            time.sleep(6)
    raise RuntimeError("❌ Could not connect to Kafka after retries.")


def run():
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT,  _handle_signal)

    logger.info("🚀 Starting InferStream Feast Push Service")

    # Ensure the shared registry directory exists (registry lives on /data volume).
    registry_dir = os.getenv("FEAST_REGISTRY_DIR", "/data/feast")
    os.makedirs(registry_dir, exist_ok=True)

    # Register the feature repo into the shared registry (idempotent).
    for i in range(10):
        if feast_client.apply_repo():
            break
        logger.warning(f"Retrying feast apply ({i+1}/10)...")
        time.sleep(6)

    consumer = connect_consumer()
    pushed = 0

    try:
        while _running:
            records = consumer.poll(timeout_ms=1000, max_records=200)
            for _tp, messages in records.items():
                for message in messages:
                    if feast_client.push_features(message.value):
                        pushed += 1
                        if pushed % 100 == 0:
                            logger.info(f"📤 Pushed {pushed:,} feature records to Feast online store")
    except Exception as e:
        logger.error(f"Push loop error: {e}")
    finally:
        consumer.close()
        logger.info(f"✅ Push service stopped. Total pushed: {pushed:,}")


if __name__ == "__main__":
    run()
