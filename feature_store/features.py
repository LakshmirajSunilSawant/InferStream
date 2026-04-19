"""
InferStream — Feast Feature Definitions
Defines entities, feature views, and feature services for
online (Redis) and offline (DuckDB) retrieval.
Prevents training/serving skew by using the same feature logic everywhere.
"""
from datetime import timedelta

from feast import (
    Entity,
    FeatureView,
    Field,
    FileSource,
    PushSource,
    FeatureService,
)
from feast.types import Float64, Int64, String, UnixTimestamp

# ─── Entity ──────────────────────────────────────────────────────────────────
stock_symbol = Entity(
    name="symbol",
    description="Stock ticker symbol (e.g. AAPL, NVDA)",
    value_type=String,
)

# ─── Data Sources ─────────────────────────────────────────────────────────────
# Online push source (real-time from Flink → Redis)
stock_push_source = PushSource(
    name="stock_push_source",
    batch_source=FileSource(
        path="/data/features_offline.parquet",
        timestamp_field="computed_at",
    ),
)

# ─── Feature Views ────────────────────────────────────────────────────────────
stock_features_view = FeatureView(
    name="stock_realtime_features",
    entities=[stock_symbol],
    ttl=timedelta(minutes=5),
    schema=[
        Field(name="avg_price_5m",   dtype=Float64),
        Field(name="momentum_1m",    dtype=Float64),
        Field(name="vwap_10m",       dtype=Float64),
        Field(name="volatility_10m", dtype=Float64),
        Field(name="trade_count_5m", dtype=Int64),
        Field(name="current_price",  dtype=Float64),
    ],
    online=True,
    source=stock_push_source,
    tags={"team": "ml-platform", "tier": "realtime"},
)

# ─── Feature Service (grouped for serving) ───────────────────────────────────
prediction_feature_service = FeatureService(
    name="stock_prediction_features",
    features=[stock_features_view],
    description="Features used for real-time stock direction prediction",
)
