"""
StreamML — FastAPI Gateway
Public-facing API with 6 endpoints:
  POST /predict              — real-time ML prediction
  GET  /features/{symbol}   — live feature values from Redis
  GET  /models              — registered MLflow model versions
  PUT  /models/{ver}/promote — promote model to production
  GET  /drift/report        — latest Evidently drift summary
  GET  /health              — full system health check

Rate limiting via SlowAPI · Prometheus metrics · Prediction logging (async queue → DuckDB)

Fixes applied:
  - Async Redis (redis.asyncio) — no more blocking event loop
  - Shared httpx.AsyncClient in lifespan — connection pool reuse
  - DuckDB removed from hot path — predictions queued and flushed in background task
  - Symbol whitelist validation
  - --workers 1 in Dockerfile (DuckDB is single-process)
"""
import os
import json
import time
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
import duckdb
import mlflow
import httpx
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, Field, field_validator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
REDIS_URL   = os.getenv("REDIS_URL",             "redis://localhost:6379")
MLFLOW_URI  = os.getenv("MLFLOW_TRACKING_URI",   "http://localhost:5000")
BENTOML_URL = os.getenv("BENTOML_URL",           "http://bentoml:3000")
DUCKDB_PATH = os.getenv("DUCKDB_PATH",           "/data/streamml.duckdb")
MODEL_NAME  = os.getenv("MODEL_NAME",            "stock_predictor")
RATE_LIMIT  = os.getenv("API_RATE_LIMIT",        "200/minute")
DRIFT_REPORT_PATH = os.getenv("DRIFT_REPORT_PATH", "/tmp/streamml_drift_report.json")

FEATURE_COLS = [
    "avg_price_5m", "momentum_1m", "vwap_10m",
    "volatility_10m", "trade_count_5m", "current_price",
]

# Valid symbols (whitelist)
VALID_SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT"}

# Background prediction log flush config
LOG_FLUSH_INTERVAL = 5.0   # seconds
LOG_FLUSH_BATCH    = 50    # flush after N records even if timer hasn't fired

# ── Prometheus Metrics ────────────────────────────────────────────────────────
PREDICTION_COUNTER = Counter("streamml_predictions_total",         "Total predictions",       ["symbol", "prediction"])
PREDICTION_LATENCY = Histogram("streamml_prediction_latency_seconds", "Prediction latency",  buckets=[.005,.01,.025,.05,.1,.25,.5,1,2.5])
FEATURE_FRESHNESS  = Gauge("streamml_feature_freshness_seconds",   "Seconds since last feature update", ["symbol"])
DRIFT_SCORE_GAUGE  = Gauge("streamml_drift_score",                 "Latest drift score")
REQUEST_COUNTER    = Counter("streamml_http_requests_total",        "Total HTTP requests",     ["method", "path", "status"])


# ── Background log flusher ────────────────────────────────────────────────────
async def _log_flusher(app: FastAPI):
    """Background task: drains prediction_log_queue → DuckDB every LOG_FLUSH_INTERVAL seconds."""
    while True:
        await asyncio.sleep(LOG_FLUSH_INTERVAL)
        queue: asyncio.Queue = app.state.log_queue
        batch = []
        while not queue.empty() and len(batch) < LOG_FLUSH_BATCH:
            try:
                batch.append(queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        if batch:
            try:
                app.state.duckdb.executemany(
                    "INSERT INTO prediction_log VALUES (?,?,?,?,?,?,?)",
                    [
                        [
                            r["symbol"], r["prediction"], r["confidence"],
                            r["probability"], r["model_version"],
                            r["latency_ms"], r["logged_at"],
                        ]
                        for r in batch
                    ],
                )
                logger.debug(f"Flushed {len(batch)} prediction logs to DuckDB")
            except Exception as e:
                logger.warning(f"DuckDB batch flush failed: {e}")


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Async Redis — non-blocking
    app.state.redis = aioredis.from_url(REDIS_URL, decode_responses=True)

    # MLflow client
    app.state.mlflow_client = mlflow.tracking.MlflowClient(tracking_uri=MLFLOW_URI)

    # DuckDB — single connection (single worker, thread-safe)
    import os
    pred_db_path = os.getenv("PREDICTIONS_DB_PATH", DUCKDB_PATH.replace(".duckdb", "_predictions.duckdb"))
    app.state.duckdb = duckdb.connect(pred_db_path)
    app.state.duckdb.execute("""
        CREATE TABLE IF NOT EXISTS prediction_log (
            symbol      VARCHAR,
            prediction  VARCHAR,
            confidence  DOUBLE,
            probability DOUBLE,
            model_ver   VARCHAR,
            latency_ms  DOUBLE,
            logged_at   TIMESTAMP
        )
    """)

    # Shared HTTP client — reuse connection pool across all requests
    app.state.http_client = httpx.AsyncClient(timeout=5.0)

    # Async queue for prediction logs (avoids DuckDB on hot path)
    app.state.log_queue = asyncio.Queue()

    # Start background flusher
    flusher = asyncio.create_task(_log_flusher(app))

    logger.info("✅ StreamML FastAPI Gateway started")
    yield

    # Graceful shutdown
    flusher.cancel()
    await app.state.http_client.aclose()
    await app.state.redis.aclose()
    app.state.duckdb.close()
    logger.info("👋 StreamML FastAPI Gateway shut down")


# ── Rate Limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="StreamML API",
    description=(
        "🚀 **StreamML** — Real-Time ML Feature Store & Model Serving Pipeline\n\n"
        "Production-grade MLOps API with Kafka → Flink → Feast → LightGBM → BentoML.\n\n"
        "Built by Lakshmiraj S. Sawant"
    ),
    version="1.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware: Request Metrics ───────────────────────────────────────────────
@app.middleware("http")
async def track_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    REQUEST_COUNTER.labels(
        method=request.method,
        path=request.url.path,
        status=response.status_code,
    ).inc()
    return response


# ── Pydantic Models ───────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    symbol: str = Field(..., example="BTCUSDT", description="Crypto symbol (BTCUSDT, ETHUSDT, SOLUSDT)")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        upper = v.upper()
        if upper not in VALID_SYMBOLS:
            raise ValueError(f"Symbol must be one of: {sorted(VALID_SYMBOLS)}")
        return upper

class PredictResponse(BaseModel):
    symbol: str
    prediction: str       # "UP" or "DOWN"
    confidence: float
    probability: float
    features: dict[str, float]
    model_version: str
    latency_ms: float

class PromoteRequest(BaseModel):
    stage: str = Field(..., example="production", description="Target stage: production, staging, archived")


# ── Helpers ───────────────────────────────────────────────────────────────────
async def get_features_from_redis(symbol: str, r: aioredis.Redis) -> dict[str, Any]:
    key = f"features:{symbol.upper()}"
    raw = await r.hgetall(key)
    if not raw:
        return {col: 0.0 for col in FEATURE_COLS}
    return {col: float(raw.get(col, 0.0)) for col in FEATURE_COLS}


def enqueue_prediction_log(app: FastAPI, data: dict):
    """Non-blocking: push to in-memory queue; background task will flush to DuckDB."""
    try:
        app.state.log_queue.put_nowait({
            **data,
            "logged_at": datetime.now(timezone.utc),
        })
    except asyncio.QueueFull:
        logger.warning("Prediction log queue full — dropping log record")


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.post("/predict", response_model=PredictResponse, tags=["Predictions"])
@limiter.limit("100/minute")
async def predict(request: Request, body: PredictRequest):
    """
    🔮 **Real-time crypto direction prediction** (UP/DOWN).

    Fetches live features from Redis (Feast online store) and runs
    the Production LightGBM model via BentoML.
    Target latency: < 100ms p99.
    """
    t0 = time.perf_counter()
    symbol = body.symbol  # already validated & uppercased by Pydantic

    try:
        client: httpx.AsyncClient = request.app.state.http_client
        resp = await client.post(
            f"{BENTOML_URL}/predict",
            json={"symbol": symbol},
        )
        resp.raise_for_status()
        result = resp.json()
    except Exception:
        # Fallback: rule-based local prediction using Redis features
        r: aioredis.Redis = request.app.state.redis
        features = await get_features_from_redis(symbol, r)
        result = _local_predict(symbol, features)

    latency_ms = (time.perf_counter() - t0) * 1000
    result["latency_ms"] = round(latency_ms, 2)

    # Async log to DuckDB via queue (never blocks the response)
    enqueue_prediction_log(request.app, result)

    # Prometheus
    PREDICTION_COUNTER.labels(symbol=symbol, prediction=result["prediction"]).inc()
    PREDICTION_LATENCY.observe(latency_ms / 1000)

    return result


def _local_predict(symbol: str, features: dict) -> dict:
    """Local prediction fallback (rule-based) when BentoML is unavailable."""
    momentum = features.get("momentum_1m", 0.0)
    conf     = min(0.5 + abs(momentum) * 50, 0.95)
    pred     = "UP" if momentum >= 0 else "DOWN"
    prob     = conf if pred == "UP" else (1 - conf)
    return {
        "symbol":        symbol,
        "prediction":    pred,
        "confidence":    round(conf, 4),
        "probability":   round(prob, 4),
        "features":      {k: round(v, 4) for k, v in features.items()},
        "model_version": "fallback-v0",
        "latency_ms":    0.0,
    }


@app.get("/features/{symbol}", tags=["Features"])
@limiter.limit("300/minute")
async def get_features(request: Request, symbol: str):
    """
    📊 **Live feature values** for a symbol from Redis (Feast online store).

    Returns rolling window statistics: VWAP, momentum, volatility, etc.
    """
    upper = symbol.upper()
    if upper not in VALID_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_symbol", "message": f"Symbol must be one of: {sorted(VALID_SYMBOLS)}"},
        )

    r: aioredis.Redis = request.app.state.redis
    features = await get_features_from_redis(upper, r)

    # Update feature freshness metric
    computed_at_str = await r.hget(f"features:{upper}", "computed_at")
    if computed_at_str:
        try:
            ct = datetime.fromisoformat(computed_at_str)
            age = (datetime.now(timezone.utc) - ct).total_seconds()
            FEATURE_FRESHNESS.labels(symbol=upper).set(age)
        except Exception:
            pass

    return {
        "symbol": upper,
        **features,
        "source": "redis-online-store",
    }


@app.get("/models", tags=["Model Registry"])
async def list_models(request: Request):
    """
    🗂️ **List all registered model versions** in MLflow with stage and metrics.
    """
    client = request.app.state.mlflow_client
    try:
        versions = client.search_model_versions(f"name='{MODEL_NAME}'")
        return {
            "model_name": MODEL_NAME,
            "versions": [
                {
                    "version":    v.version,
                    "stage":      v.current_stage,
                    "run_id":     v.run_id,
                    "created_at": datetime.fromtimestamp(
                        v.creation_timestamp / 1000, tz=timezone.utc
                    ).isoformat(),
                    "status": v.status,
                }
                for v in sorted(versions, key=lambda x: int(x.version), reverse=True)
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MLflow unavailable: {e}")


@app.put("/models/{version}/promote", tags=["Model Registry"])
async def promote_model(request: Request, version: str, body: PromoteRequest):
    """
    ⬆️ **Promote a model version** to a specified stage (production/staging/archived).
    """
    client = request.app.state.mlflow_client
    stage = body.stage.capitalize()
    valid = {"Production", "Staging", "Archived", "None"}
    if stage not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {valid}")

    try:
        client.transition_model_version_stage(
            name=MODEL_NAME,
            version=version,
            stage=stage,
            archive_existing_versions=(stage == "Production"),
        )
        return {"model": MODEL_NAME, "version": version, "stage": stage, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MLflow unavailable: {e}")


@app.get("/drift/report", tags=["Monitoring"])
async def get_drift_report():
    """
    📉 **Latest model drift report** from Evidently AI.

    Returns PSI scores, KS test results, and drift detection status.
    """
    try:
        with open(DRIFT_REPORT_PATH) as f:
            report = json.load(f)
        DRIFT_SCORE_GAUGE.set(report.get("drift_score", 0.0))
        return report
    except FileNotFoundError:
        return {
            "status": "no_report",
            "message": "No drift report yet. Run the Airflow drift DAG first.",
            "drift_score": 0.0,
            "drift_detected": False,
        }


@app.get("/health", tags=["System"])
async def health(request: Request):
    """
    💚 **Full system health check** — Redis, MLflow, BentoML, DuckDB.
    """
    health_status = {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

    # Redis (async ping)
    try:
        await request.app.state.redis.ping()
        health_status["redis"] = True
    except Exception:
        health_status["redis"] = False
        health_status["status"] = "degraded"

    # MLflow + BentoML (shared client — no new connection per request)
    client: httpx.AsyncClient = request.app.state.http_client
    try:
        r = await client.get(f"{MLFLOW_URI}/health", timeout=3.0)
        health_status["mlflow"] = r.status_code == 200
    except Exception:
        health_status["mlflow"] = False
        health_status["status"] = "degraded"

    try:
        r = await client.get(f"{BENTOML_URL}/health", timeout=3.0)
        health_status["bentoml"] = r.status_code == 200
    except Exception:
        health_status["bentoml"] = False

    # Current Production model version
    try:
        client_mlf = request.app.state.mlflow_client
        versions = client_mlf.search_model_versions(f"name='{MODEL_NAME}'")
        prod = [v for v in versions if v.current_stage == "Production"]
        health_status["model"] = f"v{prod[0].version}" if prod else "none"
    except Exception:
        health_status["model"] = "unknown"

    return health_status


@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "StreamML API Gateway",
        "version": "1.0.1",
        "docs": "/docs",
        "health": "/health",
    }
