"""
StreamML — BentoML Model Server
Loads the Production LightGBM model from MLflow,
fetches real-time features from Redis (Feast online store),
and serves predictions via REST.

Fixes applied:
  - model + Redis init moved inside __init__ (BentoML lifecycle, not module load)
  - Redis reconnection on ping/hset failure
  - Model version cache TTL for potential hot-reload
"""
import os
import json
import time
import logging
from typing import Any

import bentoml
import numpy as np
import pandas as pd
import mlflow
import mlflow.lightgbm
import redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
MLFLOW_URI  = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MODEL_NAME  = os.getenv("MODEL_NAME",          "stock_predictor")
REDIS_URL   = os.getenv("REDIS_URL",           "redis://localhost:6379")

FEATURE_COLS = [
    "avg_price_5m",
    "momentum_1m",
    "vwap_10m",
    "volatility_10m",
    "trade_count_5m",
]

LABEL_MAP = {1: "UP", 0: "DOWN"}

MODEL_CACHE_TTL = 300  # seconds: re-check MLflow for new Production model every 5 min


# ── Model loader ──────────────────────────────────────────────────────────────
def load_production_model():
    """Load champion model from MLflow Production stage."""
    mlflow.set_tracking_uri(MLFLOW_URI)
    client = mlflow.tracking.MlflowClient(tracking_uri=MLFLOW_URI)
    try:
        versions = client.search_model_versions(f"name='{MODEL_NAME}'")
        prod = [v for v in versions if v.current_stage == "Production"]
        if prod:
            v = prod[0]
            model_uri = f"models:/{MODEL_NAME}/Production"
            model = mlflow.lightgbm.load_model(model_uri)
            logger.info(f"✅ Loaded Production model v{v.version} from MLflow")
            return model, int(v.version)
    except Exception as e:
        logger.warning(f"MLflow load failed: {e} — using fallback model")
    return _fallback_model(), 0


def _fallback_model():
    """Lightweight fallback LightGBM model for cold start."""
    import lightgbm as lgb
    from sklearn.datasets import make_classification
    X, y = make_classification(n_samples=500, n_features=5, random_state=42)
    model = lgb.LGBMClassifier(n_estimators=10, verbose=-1)
    model.fit(X, y)
    logger.warning("⚠️  Using fallback random model — no Production model in MLflow")
    return model


def _connect_redis() -> redis.Redis:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    return r


# ── BentoML Service ───────────────────────────────────────────────────────────
@bentoml.service(
    name    = "streamml_predictor",
    traffic = {"timeout": 5},
    workers = 2,
)
class StockPredictionService:
    """StreamML real-time crypto direction prediction service."""

    def __init__(self):
        # Load model and Redis connection during BentoML lifecycle init
        # (not at module level, so each worker gets its own connection)
        self.model, self.model_version = load_production_model()
        self._model_loaded_at          = time.time()

        try:
            self.redis = _connect_redis()
            logger.info("✅ BentoML Redis connected")
        except Exception as e:
            logger.warning(f"Redis unavailable at init: {e}")
            self.redis = None

        logger.info(f"🚀 BentoML service initialized | model v{self.model_version}")

    def _ensure_redis(self):
        """Reconnect Redis if the connection was lost."""
        try:
            if self.redis is None:
                self.redis = _connect_redis()
            else:
                self.redis.ping()
        except Exception:
            try:
                self.redis = _connect_redis()
            except Exception as e:
                logger.error(f"Redis reconnect failed: {e}")
                self.redis = None

    def _maybe_reload_model(self):
        """Hot-reload Production model if cache TTL expired."""
        if (time.time() - self._model_loaded_at) > MODEL_CACHE_TTL:
            try:
                new_model, new_ver = load_production_model()
                if new_ver > self.model_version:
                    self.model         = new_model
                    self.model_version = new_ver
                    logger.info(f"🔄 Hot-reloaded model to v{new_ver}")
            except Exception as e:
                logger.warning(f"Model reload skipped: {e}")
            finally:
                self._model_loaded_at = time.time()

    def _get_features(self, symbol: str) -> dict[str, float]:
        """Fetch real-time features from Redis (Feast online store)."""
        self._ensure_redis()
        if self.redis is None:
            return {col: 0.0 for col in FEATURE_COLS}
        try:
            key = f"features:{symbol}"
            raw = self.redis.hgetall(key)
            if not raw:
                return {col: 0.0 for col in FEATURE_COLS}
            return {col: float(raw.get(col, 0.0)) for col in FEATURE_COLS}
        except Exception as e:
            logger.warning(f"Redis feature fetch failed: {e}")
            return {col: 0.0 for col in FEATURE_COLS}

    @bentoml.api()
    def predict(self, symbol: str) -> dict[str, Any]:
        """
        Predict short-term price direction for a crypto symbol.
        Returns: prediction (UP/DOWN), confidence, features, model_version.
        """
        self._maybe_reload_model()
        t0 = time.perf_counter()

        features = self._get_features(symbol.upper())
        X        = pd.DataFrame([features])[FEATURE_COLS]

        prob       = float(self.model.predict_proba(X)[0][1])
        pred_label = 1 if prob >= 0.5 else 0
        confidence = prob if pred_label == 1 else (1 - prob)

        latency_ms = (time.perf_counter() - t0) * 1000

        return {
            "symbol":        symbol.upper(),
            "prediction":    LABEL_MAP[pred_label],
            "confidence":    round(confidence, 4),
            "probability":   round(prob, 4),
            "features":      {k: round(v, 4) for k, v in features.items()},
            "model_version": f"v{self.model_version}",
            "latency_ms":    round(latency_ms, 2),
        }

    @bentoml.api()
    def health(self) -> dict[str, Any]:
        """Health check for the model server."""
        self._ensure_redis()
        return {
            "status":        "ok",
            "model_version": f"v{self.model_version}",
            "redis":         self.redis is not None,
        }
