"""
InferStream — Shared Constants
Single source of truth for all shared constants across the pipeline.
Import from here to prevent drift between services.
"""

# ── Feature Columns ──────────────────────────────────────────────────────────
# These MUST match in: api, flink_jobs, training, serving, monitoring
FEATURE_COLS = [
    "avg_price_5m",
    "momentum_1m",
    "vwap_10m",
    "volatility_10m",
    "trade_count_5m",
    "current_price",
]

# Training feature columns (subset — current_price is a derived input, not a model feature)
TRAINING_FEATURE_COLS = [
    "avg_price_5m",
    "momentum_1m",
    "vwap_10m",
    "volatility_10m",
    "trade_count_5m",
]

# ── Model ────────────────────────────────────────────────────────────────────
MODEL_NAME  = "stock_predictor"
LABEL_MAP   = {1: "UP", 0: "DOWN"}

# ── Symbols ──────────────────────────────────────────────────────────────────
# Binance crypto trading pairs supported by this pipeline
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

BINANCE_WS_STREAMS = "btcusdt@trade/ethusdt@trade/solusdt@trade"
BINANCE_WS_URL = f"wss://stream.binance.com:9443/stream?streams={BINANCE_WS_STREAMS}"

# ── Time Windows ─────────────────────────────────────────────────────────────
WINDOW_1M_SEC  = 60    # 1 minute in seconds
WINDOW_5M_SEC  = 300   # 5 minutes in seconds
WINDOW_10M_SEC = 600   # 10 minutes in seconds

# ── Feature Store ─────────────────────────────────────────────────────────────
FEATURE_TTL_SECONDS = 120  # Redis TTL: 2 minute freshness window

# ── Kafka Topics ─────────────────────────────────────────────────────────────
KAFKA_TOPIC_RAW       = "raw-events"
KAFKA_TOPIC_FEATURES  = "computed-features"

# ── DuckDB Batch Write ───────────────────────────────────────────────────────
DUCKDB_BATCH_SIZE     = 100   # flush after N records
DUCKDB_FLUSH_INTERVAL = 10.0  # flush after N seconds even if batch not full

# ── Feature Compute Throttle ─────────────────────────────────────────────────
FEATURE_COMPUTE_INTERVAL = 0.5  # seconds: only recompute features every 500ms
