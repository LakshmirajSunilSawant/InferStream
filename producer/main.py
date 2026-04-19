"""
InferStream — Binance WebSocket Live Data Producer
Connects to Binance's free WebSocket API to stream real-time crypto trades
(BTC, ETH, SOL) directly into Kafka.

Fixes applied:
  - Recursive on_close() → iterative reconnect loop (no stack overflow)
  - SIGTERM / SIGINT graceful shutdown
  - Backpressure callback logging
"""
import os
import json
import time
import signal
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

import websocket
from kafka import KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC           = os.getenv("KAFKA_TOPIC_RAW_EVENTS",  "raw-events")
BINANCE_WS_URL  = "wss://stream.binance.com:9443/stream?streams=btcusdt@trade/ethusdt@trade/solusdt@trade"

RECONNECT_DELAY_BASE    = 5   # initial reconnect delay (seconds)
RECONNECT_DELAY_MAX     = 60  # max reconnect delay (seconds)
RECONNECT_MAX_ATTEMPTS  = 0   # 0 = infinite (reconnect forever)


@dataclass
class StockTick:
    """Standardized event matching the downstream InferStream schema."""
    event_id:  str
    symbol:    str
    price:     float
    volume:    int
    bid:       float
    ask:       float
    timestamp: str  # ISO 8601
    source:    str = "binance-live"

    def serialize(self) -> bytes:
        return json.dumps(asdict(self)).encode("utf-8")


def create_producer(max_retries: int = 10) -> KafkaProducer:
    """Create Kafka producer with exponential back-off retry."""
    for attempt in range(1, max_retries + 1):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: v,   # already bytes
                acks="all",
                retries=5,
                linger_ms=5,
                batch_size=16_384,
                compression_type="gzip",
            )
            logger.info(f"✅ Connected to Kafka at {KAFKA_BOOTSTRAP}")
            return producer
        except KafkaError as e:
            logger.warning(f"Attempt {attempt}/{max_retries}: Kafka not ready — {e}")
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError("Could not connect to Kafka after retries.")


class BinanceLiveStreamer:
    """Manages the WebSocket connection and Kafka publishing."""

    def __init__(self):
        self.producer    = create_producer()
        self.sent_count  = 0
        self.last_prices = {"BTCUSDT": 0.0, "ETHUSDT": 0.0, "SOLUSDT": 0.0}
        self._running    = True

        # Graceful shutdown on SIGTERM / SIGINT
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT,  self._handle_signal)

    def _handle_signal(self, signum, frame):
        logger.info(f"🛑 Received signal {signum} — stopping producer...")
        self._running = False

    # ── WebSocket callbacks ──────────────────────────────────────────────
    def on_message(self, ws, message):
        """Parse Binance payload and fire into Kafka."""
        try:
            data = json.loads(message)
            if "data" not in data:
                return

            payload  = data["data"]
            symbol   = payload.get("s", "UNKNOWN")
            price    = float(payload.get("p", 0.0))
            quantity = float(payload.get("q", 0.0))
            ts_ms    = int(payload.get("T", int(time.time() * 1000)))
            event_id = str(payload.get("t", int(time.time() * 1000)))

            self.last_prices[symbol] = price

            volume = int(quantity * (1000 if symbol == "BTCUSDT" else 100))
            spread = price * 0.0001

            tick = StockTick(
                event_id  = f"B-{symbol}-{event_id}",
                symbol    = symbol,
                price     = price,
                volume    = max(volume, 1),
                bid       = round(price - spread / 2, 4),
                ask       = round(price + spread / 2, 4),
                timestamp = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat(),
            )

            future = self.producer.send(
                TOPIC,
                key=tick.symbol.encode(),
                value=tick.serialize(),
            )
            future.add_errback(self._on_send_error)
            self.sent_count += 1

            if self.sent_count % 100 == 0:
                logger.info(
                    f"📤 Sent {self.sent_count:,} live trades | "
                    f"BTC=${self.last_prices['BTCUSDT']:,.2f} | "
                    f"ETH=${self.last_prices['ETHUSDT']:,.2f} | "
                    f"SOL=${self.last_prices['SOLUSDT']:,.2f}"
                )

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _on_send_error(self, *args, **kwargs):
        logger.error(f"Kafka send error: {args} {kwargs}")

    def on_error(self, ws, error):
        logger.error(f"WebSocket Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        # Do NOT call self.start() here — that causes infinite recursion.
        # The iterative loop in start() handles reconnection.
        logger.warning(f"🔴 WebSocket closed (code={close_status_code})")

    def on_open(self, ws):
        logger.info(f"✅ Connected to Binance WebSocket")

    # ── Iterative reconnect loop ─────────────────────────────────────────
    def start(self):
        """Run with iterative reconnect — no recursion, no stack overflow."""
        logger.info("🚀 Starting InferStream Live Crypto Producer...")
        websocket.enableTrace(False)
        delay = RECONNECT_DELAY_BASE

        while self._running:
            try:
                ws = websocket.WebSocketApp(
                    BINANCE_WS_URL,
                    on_open    = self.on_open,
                    on_message = self.on_message,
                    on_error   = self.on_error,
                    on_close   = self.on_close,
                )
                ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                logger.error(f"WebSocket exception: {e}")

            if not self._running:
                break

            logger.warning(f"🔁 Reconnecting in {delay}s...")
            time.sleep(delay)
            delay = min(delay * 2, RECONNECT_DELAY_MAX)  # exponential back-off

        self.producer.flush()
        self.producer.close()
        logger.info("✅ Producer shut down cleanly.")


def run_producer():
    streamer = BinanceLiveStreamer()
    streamer.start()


if __name__ == "__main__":
    run_producer()
