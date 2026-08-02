"""
InferStream — PyFlink Feature Computation Job (real Apache Flink DataStream API)

Runs an embedded Flink MiniCluster inside this container (env.execute() with no
remote JobManager configured). The pipeline is a genuine stateful stream:

    KafkaSource(raw-events)
        --> map(parse JSON tick -> Row)
        --> keyBy(symbol)
        --> KeyedProcessFunction (managed keyed state: sliding tick buffer)
              side effects: write online features to Redis + offline rows to DuckDB
              emits: computed-feature JSON (throttled per symbol)
        --> KafkaSink(computed-features)      # consumed by the Feast push service

Features computed (per symbol):
  - avg_price_5m     : 5-minute rolling average price
  - momentum_1m      : price momentum vs 1-min avg
  - vwap_10m         : 10-min volume-weighted average price
  - volatility_10m   : 10-min price std deviation
  - trade_count_5m   : number of ticks in last 5 minutes
  - current_price    : latest trade price

State is held in Flink keyed ListState/ValueState (checkpointed), so this is
stateful stream processing — not an in-memory dict that dies with the process.
"""
import os
import json
import time
import glob
import logging
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import redis
import duckdb

from pyflink.common import Types, WatermarkStrategy, Configuration
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream import (
    StreamExecutionEnvironment,
    KeyedProcessFunction,
    RuntimeContext,
)
from pyflink.datastream.state import ListStateDescriptor, ValueStateDescriptor
from pyflink.datastream.connectors.kafka import (
    KafkaSource,
    KafkaSink,
    KafkaOffsetsInitializer,
    KafkaRecordSerializationSchema,
    DeliveryGuarantee,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP  = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_RAW        = os.getenv("KAFKA_TOPIC_RAW_EVENTS",  "raw-events")
TOPIC_FEATURES   = os.getenv("KAFKA_TOPIC_FEATURES",    "computed-features")
REDIS_URL        = os.getenv("REDIS_URL",               "redis://localhost:6379")
DUCKDB_PATH      = os.getenv("DUCKDB_PATH",             "/data/inferstream.duckdb")

WINDOW_5M_SEC  = 300    # 5 minutes
WINDOW_1M_SEC  = 60     # 1 minute
WINDOW_10M_SEC = 600    # 10 minutes  (== max retained window)
FEATURE_TTL    = 120    # Redis TTL in seconds

DUCKDB_BATCH_SIZE     = int(os.getenv("DUCKDB_BATCH_SIZE",     "100"))
DUCKDB_FLUSH_INTERVAL = float(os.getenv("DUCKDB_FLUSH_INTERVAL", "10.0"))

# Only recompute + emit features every N seconds per symbol
FEATURE_COMPUTE_INTERVAL = float(os.getenv("FEATURE_COMPUTE_INTERVAL", "0.5"))

# Directory where the Dockerfile drops the Flink Kafka connector fat-JAR
FLINK_JARS_DIR = os.getenv("FLINK_JARS_DIR", "/opt/flink-jars")


# ── Pure feature math (kept small + unit-testable) ────────────────────────────
def _avg_price(rows: list[tuple[float, float, int]], cutoff: float) -> float:
    prices = [p for (ts, p, v) in rows if ts >= cutoff]
    return sum(prices) / len(prices) if prices else 0.0


def _vwap(rows: list[tuple[float, float, int]], cutoff: float) -> float:
    total_vol = sum(v for (ts, p, v) in rows if ts >= cutoff)
    if total_vol == 0:
        return 0.0
    return sum(p * v for (ts, p, v) in rows if ts >= cutoff) / total_vol


def _volatility(rows: list[tuple[float, float, int]], cutoff: float) -> float:
    prices = [p for (ts, p, v) in rows if ts >= cutoff]
    if len(prices) < 2:
        return 0.0
    mean = sum(prices) / len(prices)
    variance = sum((x - mean) ** 2 for x in prices) / len(prices)
    return variance ** 0.5


def _count(rows: list[tuple[float, float, int]], cutoff: float) -> int:
    return sum(1 for (ts, p, v) in rows if ts >= cutoff)


def compute_features(symbol: str, rows: list[tuple[float, float, int]],
                     current_price: float, now_event_ts: float) -> dict:
    """Compute all windowed features from the retained (<=10m) tick buffer."""
    avg_5m   = _avg_price(rows, now_event_ts - WINDOW_5M_SEC)
    avg_1m   = _avg_price(rows, now_event_ts - WINDOW_1M_SEC)
    vwap_10m = _vwap(rows, now_event_ts - WINDOW_10M_SEC)
    vol_10m  = _volatility(rows, now_event_ts - WINDOW_10M_SEC)
    count_5m = _count(rows, now_event_ts - WINDOW_5M_SEC)
    momentum = ((current_price - avg_1m) / avg_1m) if avg_1m > 0 else 0.0

    return {
        "symbol":         symbol,
        "avg_price_5m":   round(avg_5m, 4),
        "momentum_1m":    round(momentum, 6),
        "vwap_10m":       round(vwap_10m, 4),
        "volatility_10m": round(vol_10m, 6),
        "trade_count_5m": count_5m,
        "current_price":  round(current_price, 4),
        "computed_at":    datetime.now(timezone.utc).isoformat(),
    }


# ── DuckDB offline store ──────────────────────────────────────────────────────
def init_duckdb(path: str) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_ticks (
            event_id VARCHAR, symbol VARCHAR, price DOUBLE, volume INTEGER,
            bid DOUBLE, ask DOUBLE, event_ts TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS computed_features (
            symbol VARCHAR, avg_price_5m DOUBLE, momentum_1m DOUBLE,
            vwap_10m DOUBLE, volatility_10m DOUBLE, trade_count_5m INTEGER,
            computed_at TIMESTAMP
        )
    """)
    logger.info(f"✅ DuckDB initialized at {path}")
    return conn


# ── The stateful Flink operator ───────────────────────────────────────────────
class FeatureProcessFunction(KeyedProcessFunction):
    """
    Per-symbol stateful feature computation.

    Keyed state (managed by Flink, checkpointed):
      - `ticks`        : ListState[(event_ts, price, volume)] within the 10m window
      - `last_compute` : ValueState[float] wall-clock of the last emit (throttle)

    Operator-local (per-subtask) resources initialised in open():
      - Redis client (online store, bridge/fast path)
      - DuckDB connection + batched write buffers (offline store)

    Emits: the computed-feature JSON string (for the Kafka `computed-features`
    sink, which the Feast push service consumes).
    """

    def __init__(self):
        self.ticks: Optional[Any] = None
        self.last_compute: Optional[Any] = None
        self.redis: Optional[redis.Redis] = None
        self.duckdb: Optional[duckdb.DuckDBPyConnection] = None
        self.tick_buffer: list = []
        self.feature_buffer: list = []
        self.last_flush: float = 0.0
        self.processed: int = 0

    def open(self, runtime_context: RuntimeContext):
        # Keyed state descriptors
        self.ticks = runtime_context.get_list_state(
            ListStateDescriptor(
                "ticks",
                Types.TUPLE([Types.DOUBLE(), Types.DOUBLE(), Types.INT()]),
            )
        )
        self.last_compute = runtime_context.get_state(
            ValueStateDescriptor("last_compute", Types.DOUBLE())
        )

        # Online store (Redis) — bridge/fast path; also read directly by the API fallback
        try:
            self.redis = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis.ping()
            logger.info("✅ Flink operator connected to Redis")
        except Exception as e:
            logger.warning(f"Redis unavailable at open(): {e}")
            self.redis = None

        # Offline store (DuckDB)
        self.duckdb = init_duckdb(DUCKDB_PATH)
        self.last_flush = time.time()

    def close(self):
        self._flush_duckdb()
        try:
            if self.duckdb is not None:
                self.duckdb.close()
        except Exception:
            pass

    # ── helpers ──────────────────────────────────────────────────────────────
    def _ensure_redis(self):
        try:
            if self.redis is None:
                self.redis = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis.ping()
        except Exception:
            try:
                self.redis = redis.from_url(REDIS_URL, decode_responses=True)
                self.redis.ping()
            except Exception:
                self.redis = None

    def _write_redis(self, features: dict):
        self._ensure_redis()
        if self.redis is None:
            return
        try:
            key = f"features:{features['symbol']}"
            self.redis.hset(key, mapping={k: str(v) for k, v in features.items()})
            self.redis.expire(key, FEATURE_TTL)
        except Exception as e:
            logger.warning(f"Redis write failed: {e}")

    def _flush_duckdb(self):
        if self.tick_buffer:
            try:
                self.duckdb.executemany(
                    "INSERT INTO raw_ticks VALUES (?,?,?,?,?,?,?)", self.tick_buffer
                )
            except Exception as e:
                logger.warning(f"DuckDB raw_ticks flush failed: {e}")
            self.tick_buffer.clear()
        if self.feature_buffer:
            try:
                self.duckdb.executemany(
                    "INSERT INTO computed_features VALUES (?,?,?,?,?,?,?)",
                    self.feature_buffer,
                )
            except Exception as e:
                logger.warning(f"DuckDB computed_features flush failed: {e}")
            self.feature_buffer.clear()

    # ── per-element processing ───────────────────────────────────────────────
    def process_element(self, value, ctx: "KeyedProcessFunction.Context") -> Iterable[str]:
        # value is a Row(symbol, price, volume, event_ts)
        symbol   = value[0]
        price    = float(value[1])
        volume   = int(value[2])
        event_ts = float(value[3])

        # ── update keyed sliding-window state (evict > 10m old) ──────────────
        cutoff = event_ts - WINDOW_10M_SEC
        retained: list[tuple[float, float, int]] = [
            (ts, p, v) for (ts, p, v) in self.ticks.get() if ts >= cutoff
        ]
        retained.append((event_ts, price, volume))
        self.ticks.update(retained)

        now = time.time()

        # Buffer the raw tick for the offline store (every message)
        self.tick_buffer.append([
            "", symbol, price, volume, 0.0, 0.0, datetime.now(timezone.utc),
        ])

        # ── throttled feature compute + emit ─────────────────────────────────
        last = self.last_compute.value()
        emitted: Optional[str] = None
        if last is None or (now - last) >= FEATURE_COMPUTE_INTERVAL:
            features = compute_features(symbol, retained, price, event_ts)
            self.last_compute.update(now)

            self._write_redis(features)                       # online (bridge)
            self.feature_buffer.append([                      # offline
                symbol, features["avg_price_5m"], features["momentum_1m"],
                features["vwap_10m"], features["volatility_10m"],
                features["trade_count_5m"], datetime.now(timezone.utc),
            ])
            emitted = json.dumps(features)                    # -> Kafka -> Feast

        # ── batched DuckDB flush ─────────────────────────────────────────────
        self.processed += 1
        if (len(self.tick_buffer) >= DUCKDB_BATCH_SIZE
                or (now - self.last_flush) >= DUCKDB_FLUSH_INTERVAL):
            self._flush_duckdb()
            self.last_flush = now

        if self.processed % 500 == 0:
            logger.info(f"⚡ Processed {self.processed:,} ticks (this subtask)")

        if emitted is not None:
            yield emitted


# ── Job assembly ──────────────────────────────────────────────────────────────
def _discover_connector_jar() -> Optional[str]:
    matches = sorted(glob.glob(os.path.join(FLINK_JARS_DIR, "flink-sql-connector-kafka*.jar")))
    return matches[0] if matches else None


def build_env() -> StreamExecutionEnvironment:
    config = Configuration()
    env = StreamExecutionEnvironment.get_execution_environment(config)

    # DuckDB is a single-writer file; keep the whole pipeline single-parallel so
    # exactly one operator instance owns the connection.
    env.set_parallelism(1)

    # Genuine stateful streaming: snapshot keyed window state every 30s.
    env.enable_checkpointing(30_000)
    env.get_checkpoint_config().set_checkpoint_storage_dir(
        os.getenv("FLINK_CHECKPOINT_DIR", "file:///tmp/flink-checkpoints")
    )

    jar = _discover_connector_jar()
    if not jar:
        raise RuntimeError(
            f"Kafka connector JAR not found in {FLINK_JARS_DIR}. "
            "The Dockerfile must download flink-sql-connector-kafka-*.jar there."
        )
    env.add_jars(f"file://{jar}")
    logger.info(f"✅ Added Flink Kafka connector JAR: {jar}")
    return env


def parse_tick(raw: str):
    """JSON line -> Row(symbol, price, volume, event_ts)."""
    from pyflink.common import Row
    try:
        tick = json.loads(raw)
    except Exception:
        return Row("UNKNOWN", 0.0, 0, time.time())
    symbol = tick.get("symbol", "UNKNOWN")
    price  = float(tick.get("price", 0.0))
    volume = int(tick.get("volume", 0))
    try:
        event_ts = datetime.fromisoformat(tick.get("timestamp", "")).timestamp()
    except Exception:
        event_ts = time.time()
    return Row(symbol, price, volume, event_ts)


def run_flink_job():
    logger.info("🔥 InferStream PyFlink Feature Job starting (embedded MiniCluster)")
    env = build_env()

    row_type = Types.ROW_NAMED(
        ["symbol", "price", "volume", "event_ts"],
        [Types.STRING(), Types.DOUBLE(), Types.INT(), Types.DOUBLE()],
    )

    source = (
        KafkaSource.builder()
        .set_bootstrap_servers(KAFKA_BOOTSTRAP)
        .set_topics(TOPIC_RAW)
        .set_group_id("flink-feature-job")
        .set_starting_offsets(KafkaOffsetsInitializer.latest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )

    sink = (
        KafkaSink.builder()
        .set_bootstrap_servers(KAFKA_BOOTSTRAP)
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder()
            .set_topic(TOPIC_FEATURES)
            .set_value_serialization_schema(SimpleStringSchema())
            .build()
        )
        .set_delivery_guarantee(DeliveryGuarantee.AT_LEAST_ONCE)
        .build()
    )

    stream = env.from_source(source, WatermarkStrategy.no_watermarks(), "kafka-raw-events")

    features = (
        stream
        .map(parse_tick, output_type=row_type)
        .key_by(lambda r: r[0], key_type=Types.STRING())
        .process(FeatureProcessFunction(), output_type=Types.STRING())
        .name("feature-compute")
    )

    features.sink_to(sink).name("kafka-computed-features")

    logger.info(f"✅ Pipeline wired: {TOPIC_RAW} -> features -> {TOPIC_FEATURES}")
    env.execute("InferStream Flink Feature Job")


if __name__ == "__main__":
    run_flink_job()
