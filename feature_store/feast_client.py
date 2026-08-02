"""
InferStream — Feast client helpers.

One place that knows how to:
  - apply the feature repo (register entity/view/service into the registry)
  - push streaming features into the online store  (writer: push_service.py)
  - read features back out of the online store      (reader: api)

Self-contained (no cross-package imports) so it works whether it's imported as
`feast_client` (push service) or `feature_store.feast_client` (api).
"""
import os
import logging
import subprocess
from functools import lru_cache

logger = logging.getLogger(__name__)

# Directory containing feature_store.yaml + features.py
REPO_PATH = os.getenv("FEAST_REPO_PATH", "/app/feature_store")

FEATURE_VIEW = "stock_realtime_features"
PUSH_SOURCE  = "stock_push_source"

# Must match the schema in features.py
FEATURE_COLS = [
    "avg_price_5m",
    "momentum_1m",
    "vwap_10m",
    "volatility_10m",
    "trade_count_5m",
    "current_price",
]
FEATURE_REFS = [f"{FEATURE_VIEW}:{c}" for c in FEATURE_COLS]

# Parquet backing the PushSource's batch_source (see features.py). Nothing on the
# online path reads it, but `feast apply` opens it to validate the source, so it
# has to exist before the registry can be applied.
BATCH_SOURCE_PATH = os.getenv("FEAST_BATCH_SOURCE_PATH", "/data/features_offline.parquet")

# Must mirror the Field dtypes in features.py
_BATCH_DTYPES = {
    "symbol":         "string",
    "computed_at":    "datetime64[ns, UTC]",
    "avg_price_5m":   "float64",
    "momentum_1m":    "float64",
    "vwap_10m":       "float64",
    "volatility_10m": "float64",
    "trade_count_5m": "int64",
    "current_price":  "float64",
}


def ensure_batch_source(path: str = BATCH_SOURCE_PATH) -> None:
    """Seed an empty, correctly-typed parquet for the batch source if it's missing."""
    if os.path.exists(path):
        return
    import pandas as pd

    os.makedirs(os.path.dirname(path), exist_ok=True)
    empty = pd.DataFrame({c: pd.Series(dtype=d) for c, d in _BATCH_DTYPES.items()})
    empty.to_parquet(path, index=False)
    logger.info(f"📄 Seeded empty batch source at {path}")


@lru_cache(maxsize=1)
def get_store():
    """Return a cached FeatureStore bound to the repo. Imports feast lazily so
    a missing/broken feast install never crashes the importing service."""
    from feast import FeatureStore
    return FeatureStore(repo_path=REPO_PATH)


def apply_repo() -> bool:
    """Register the feature definitions into the shared registry. Idempotent."""
    try:
        ensure_batch_source()
        subprocess.run(
            ["feast", "apply"],
            cwd=REPO_PATH,
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("✅ feast apply complete (registry updated)")
        get_store.cache_clear()
        return True
    except Exception as e:
        detail = getattr(e, "stderr", "") or str(e)
        logger.error(f"feast apply failed: {detail}")
        return False


def push_features(feature_row: dict) -> bool:
    """Push one computed-feature record into the Feast online store.

    `feature_row` carries the 6 feature fields + `symbol` + `computed_at` (ISO).
    """
    import pandas as pd
    from feast.data_source import PushMode

    try:
        row = {
            "symbol":       feature_row["symbol"],
            "computed_at":  pd.to_datetime(feature_row["computed_at"], utc=True),
        }
        for col in FEATURE_COLS:
            row[col] = feature_row.get(col, 0.0)

        df = pd.DataFrame([row])
        get_store().push(PUSH_SOURCE, df, to=PushMode.ONLINE)
        return True
    except Exception as e:
        logger.warning(f"Feast push failed for {feature_row.get('symbol')}: {e}")
        return False


def get_online_features(symbol: str) -> dict:
    """Read the latest features for one symbol from the Feast online store.

    Returns {col: float} for all FEATURE_COLS. Raises on failure so callers can
    decide whether to fall back — see the API's raw-Redis fallback.
    """
    store = get_store()
    resp = store.get_online_features(
        features=FEATURE_REFS,
        entity_rows=[{"symbol": symbol.upper()}],
    ).to_dict()

    out = {}
    for col in FEATURE_COLS:
        vals = resp.get(col) or [None]
        out[col] = float(vals[0]) if vals[0] is not None else 0.0
    return out
