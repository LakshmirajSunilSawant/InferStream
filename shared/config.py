"""
InferStream — Centralized Configuration
All environment variables with typed defaults in one place.
Works with plain os.getenv (no pydantic-settings required) so it runs in
every service without additional dependencies.
"""
import os


class Settings:
    """Singleton-style config object. Read env vars once at startup."""

    # ── Kafka ─────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_RAW_EVENTS: str  = os.getenv("KAFKA_TOPIC_RAW_EVENTS",  "raw-events")
    KAFKA_TOPIC_FEATURES: str    = os.getenv("KAFKA_TOPIC_FEATURES",     "computed-features")

    # ── Redis ─────────────────────────────────────────────────────────────
    # Docker default: redis://redis:6379
    # Local default:  redis://localhost:6379
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # ── DuckDB ───────────────────────────────────────────────────────────
    # Docker: /data/inferstream.duckdb  (mounted duckdb-data volume)
    # Local:  ./data/inferstream.duckdb
    DUCKDB_PATH: str = os.getenv("DUCKDB_PATH", "/data/inferstream.duckdb")

    # ── MLflow ───────────────────────────────────────────────────────────
    MLFLOW_TRACKING_URI: str    = os.getenv("MLFLOW_TRACKING_URI",    "http://localhost:5000")
    MLFLOW_EXPERIMENT_NAME: str = os.getenv("MLFLOW_EXPERIMENT_NAME", "inferstream-stock-prediction")

    # ── API ───────────────────────────────────────────────────────────────
    BENTOML_URL: str    = os.getenv("BENTOML_URL",    "http://bentoml:3000")
    API_RATE_LIMIT: str = os.getenv("API_RATE_LIMIT", "200/minute")
    API_URL: str        = os.getenv("API_URL",        "http://localhost:8000")

    # ── Model ─────────────────────────────────────────────────────────────
    MODEL_NAME: str       = os.getenv("MODEL_NAME",      "stock_predictor")
    DRIFT_THRESHOLD: float = float(os.getenv("DRIFT_THRESHOLD", "0.2"))

    # ── Monitoring ────────────────────────────────────────────────────────
    # Use env-configurable paths rather than hardcoded /tmp
    DRIFT_REPORT_PATH: str      = os.getenv("DRIFT_REPORT_PATH",      "/tmp/inferstream_drift_report.json")
    DRIFT_HTML_REPORT_PATH: str = os.getenv("DRIFT_HTML_REPORT_PATH", "/tmp/inferstream_drift_report.html")


settings = Settings()
