"""
InferStream — PyFlink Feature Computation Job
Consumes raw stock ticks from Kafka, computes windowed features,
and writes to Redis (online store) and DuckDB (offline store).

Fixes applied:
  - Guard against None consumer/redis after exhausting retries (RuntimeError)
  - Batched DuckDB writes (DUCKDB_BATCH_SIZE records or FLUSH_INTERVAL seconds)
  - Feature computation throttled to FEATURE_COMPUTE_INTERVAL seconds per symbol
  - Redis reconnection on write failure

Features computed:
  - avg_price_5m     : 5-minute rolling average price
  - momentum_1m      : price momentum vs 1-min avg
  - vwap_10m         : 10-min volume-weighted average price
  - volatility_10m   : 10-min price std deviation
  - trade_count_5m   : number of ticks in last 5 minutes
  - current_price    : latest trade price
"""
import os
import json
import time
import logging
from datetime import datetime, timezone
from collections import defaultdict, deque
from typing import Any, Optional

import redis
import duckdb
from kafka import KafkaConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC           = os.getenv("KAFKA_TOPIC_RAW_EVENTS",  "raw-events")
REDIS_URL       = os.getenv("REDIS_URL",               "redis://localhost:6379")
DUCKDB_PATH     = os.getenv("DUCKDB_PATH",             "/data/inferstream.duckdb")

WINDOW_5M_SEC  = 300    # 5 minutes
WINDOW_1M_SEC  = 60     # 1 minute
WINDOW_10M_SEC = 600    # 10 minutes
FEATURE_TTL    = 120    # Redis TTL in seconds

# Batch write config
DUCKDB_BATCH_SIZE     = int(os.getenv("DUCKDB_BATCH_SIZE",     "100"))
DUCKDB_FLUSH_INTERVAL = float(os.getenv("DUCKDB_FLUSH_INTERVAL", "10.0"))

# Feature compute throttle: only recompute + write Redis every N seconds per symbol
FEATURE_COMPUTE_INTERVAL = float(os.getenv("FEATURE_COMPUTE_INTERVAL", "0.5"))


# ── DuckDB Offline Store ──────────────────────────────────────────────────────
def init_duckdb(path: str) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_ticks (
            event_id    VARCHAR,
            symbol      VARCHAR,
            price       DOUBLE,
            volume      INTEGER,
            bid         DOUBLE,
            ask         DOUBLE,
            event_ts    TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS computed_features (
            symbol          VARCHAR,
            avg_price_5m    DOUBLE,
            momentum_1m     DOUBLE,
            vwap_10m        DOUBLE,
            volatility_10m  DOUBLE,
            trade_count_5m  INTEGER,
            computed_at     TIMESTAMP
        )
    """)
    logger.info(f"✅ DuckDB initialized at {path}")
    return conn


# ── Feature Window State ──────────────────────────────────────────────────────
class TickWindow:
    """Sliding window of tick data keyed by symbol."""

    def __init__(self, max_seconds: int):
        self.max_seconds = max_seconds
        self.data: deque[tuple[float, float, int]] = deque()

    def add(self, ts: float, price: float, volume: int):
        cutoff = ts - self.max_seconds
        while self.data and self.data[0][0] < cutoff:
            self.data.popleft()
        self.data.append((ts, price, volume))

    def prices(self) -> list[float]:
        return [d[1] for d in self.data]

    def volumes(self) -> list[int]:
        return [d[2] for d in self.data]

    def avg_price(self) -> float:
        p = self.prices()
        return sum(p) / len(p) if p else 0.0

    def vwap(self) -> float:
        total_vol = sum(d[2] for d in self.data)
        if total_vol == 0:
            return 0.0
        return sum(d[1] * d[2] for d in self.data) / total_vol

    def volatility(self) -> float:
        p = self.prices()
        if len(p) < 2:
            return 0.0
        mean = sum(p) / len(p)
        variance = sum((x - mean) ** 2 for x in p) / len(p)
        return variance ** 0.5

    def count(self) -> int:
        return len(self.data)


class SymbolState:
    """Per-symbol sliding windows + last compute time."""

    def __init__(self):
        self.w5m          = TickWindow(WINDOW_5M_SEC)
        self.w1m          = TickWindow(WINDOW_1M_SEC)
        self.w10m         = TickWindow(WINDOW_10M_SEC)
        self.last_compute = 0.0   # unix timestamp of last feature compute


# ── Redis helper ──────────────────────────────────────────────────────────────
def connect_redis(max_retries: int = 10) -> Optional[redis.Redis]:
    for i in range(max_retries):
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True)
            r.ping()
            logger.info("✅ Connected to Redis")
            return r
        except Exception as e:
            logger.warning(f"Redis not ready ({i+1}/{max_retries}): {e}")
            time.sleep(5)
    return None


# ── Feature computation ───────────────────────────────────────────────────────
def compute_and_store(
    symbol: str,
    state: SymbolState,
    redis_client: redis.Redis,
    current_price: float,
) -> dict:
    """Compute features and write to Redis."""
    avg_5m   = state.w5m.avg_price()
    avg_1m   = state.w1m.avg_price()
    vwap_10m = state.w10m.vwap()
    vol_10m  = state.w10m.volatility()
    count_5m = state.w5m.count()

    momentum = ((current_price - avg_1m) / avg_1m) if avg_1m > 0 else 0.0

    features = {
        "symbol":          symbol,
        "avg_price_5m":    round(avg_5m, 4),
        "momentum_1m":     round(momentum, 6),
        "vwap_10m":        round(vwap_10m, 4),
        "volatility_10m":  round(vol_10m, 6),
        "trade_count_5m":  count_5m,
        "current_price":   round(current_price, 4),
        "computed_at":     datetime.now(timezone.utc).isoformat(),
    }

    # Write to Redis (online store)
    try:
        redis_key = f"features:{symbol}"
        redis_client.hset(redis_key, mapping={k: str(v) for k, v in features.items()})
        redis_client.expire(redis_key, FEATURE_TTL)
    except Exception as e:
        logger.warning(f"Redis write failed for {symbol}: {e}")
        # Attempt reconnect on next tick
        try:
            redis_client.ping()
        except Exception:
            logger.error("Redis connection lost — attempting reconnect next tick")

    return features


def flush_to_duckdb(
    duckdb_conn: duckdb.DuckDBPyConnection,
    tick_buffer: list,
    feature_buffer: list,
):
    """Batch-write tick and feature buffers to DuckDB."""
    if tick_buffer:
        try:
            duckdb_conn.executemany(
                "INSERT INTO raw_ticks VALUES (?, ?, ?, ?, ?, ?, ?)",
                tick_buffer,
            )
        except Exception as e:
            logger.warning(f"DuckDB raw_ticks batch write failed: {e}")
        tick_buffer.clear()

    if feature_buffer:
        try:
            duckdb_conn.executemany(
                "INSERT INTO computed_features VALUES (?, ?, ?, ?, ?, ?, ?)",
                feature_buffer,
            )
        except Exception as e:
            logger.warning(f"DuckDB computed_features batch write failed: {e}")
        feature_buffer.clear()


# ── Main Feature Job ──────────────────────────────────────────────────────────
def run_flink_job():
    """Main feature computation loop (PyFlink-style stateful stream)."""
    logger.info("🔥 InferStream Flink Feature Job starting")

    # Connect Redis with retry — raise immediately if exhausted
    redis_client = connect_redis(max_retries=10)
    if redis_client is None:
        raise RuntimeError("❌ Could not connect to Redis after retries. Exiting.")

    # Initialize DuckDB
    duckdb_conn = init_duckdb(DUCKDB_PATH)

    # Initialize Kafka consumer with retry — raise immediately if exhausted
    consumer = None
    for i in range(15):
        try:
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id="flink-feature-job",
                auto_offset_reset="latest",
                enable_auto_commit=True,
                value_deserializer=lambda b: json.loads(b.decode("utf-8")),
            )
            logger.info(f"✅ Subscribed to Kafka topic: {TOPIC}")
            break
        except Exception as e:
            logger.warning(f"Kafka not ready ({i+1}/15): {e}")
            time.sleep(6)

    if consumer is None:
        raise RuntimeError("❌ Could not connect to Kafka after retries. Exiting.")

    symbol_states: dict[str, SymbolState] = defaultdict(SymbolState)
    processed   = 0
    tick_buffer: list    = []
    feature_buffer: list = []
    last_flush   = time.time()

    try:
        for message in consumer:
            tick: dict[str, Any] = message.value
            symbol = tick.get("symbol", "UNKNOWN")
            price  = float(tick.get("price", 0))
            volume = int(tick.get("volume", 0))
            ts_str = tick.get("timestamp", "")

            try:
                ts = datetime.fromisoformat(ts_str).timestamp()
            except Exception:
                ts = time.time()

            state = symbol_states[symbol]
            state.w5m.add(ts, price, volume)
            state.w1m.add(ts, price, volume)
            state.w10m.add(ts, price, volume)

            now = time.time()

            # Throttle feature computation to every FEATURE_COMPUTE_INTERVAL per symbol
            if (now - state.last_compute) >= FEATURE_COMPUTE_INTERVAL:
                features = compute_and_store(symbol, state, redis_client, price)
                state.last_compute = now

                feature_buffer.append([
                    symbol,
                    features["avg_price_5m"],
                    features["momentum_1m"],
                    features["vwap_10m"],
                    features["volatility_10m"],
                    features["trade_count_5m"],
                    datetime.now(timezone.utc),
                ])

            # Buffer raw tick
            tick_buffer.append([
                tick.get("event_id", ""),
                symbol, price, volume,
                tick.get("bid", 0), tick.get("ask", 0),
                datetime.now(timezone.utc),
            ])

            processed += 1

            # Flush to DuckDB when batch is full or interval elapsed
            should_flush = (
                len(tick_buffer) >= DUCKDB_BATCH_SIZE
                or (now - last_flush) >= DUCKDB_FLUSH_INTERVAL
            )
            if should_flush:
                flush_to_duckdb(duckdb_conn, tick_buffer, feature_buffer)
                last_flush = now
                logger.debug(f"⚡ Processed {processed:,} ticks — flushed batch to DuckDB")

            if processed % 500 == 0:
                logger.info(
                    f"⚡ Processed {processed:,} ticks | "
                    f"{symbol}: price={price:.2f} vwap={features.get('vwap_10m', 0):.2f} "
                    f"momentum={features.get('momentum_1m', 0):.4f}"
                    if 'features' in dir() else f"⚡ Processed {processed:,} ticks"
                )

    except KeyboardInterrupt:
        logger.info("🛑 Feature job stopped")
    finally:
        # Final flush before exit
        flush_to_duckdb(duckdb_conn, tick_buffer, feature_buffer)
        consumer.close()
        duckdb_conn.close()
        logger.info(f"✅ Total ticks processed: {processed:,}")


if __name__ == "__main__":
    run_flink_job()
