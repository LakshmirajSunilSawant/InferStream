"""
InferStream — Feast Feature Definitions
Defines the entity, push source, feature view, and feature service used for
online (Redis) retrieval. The SAME definitions back both the streaming push
(feature_store/push_service.py) and the online reads (api), so training and
serving share one feature contract — no skew.
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
from feast.types import Float64, Int64

# ─── Entity ──────────────────────────────────────────────────────────────────
# join_keys is the modern Feast API (value_type is deprecated).
symbol = Entity(
    name="symbol",
    join_keys=["symbol"],
    description="Binance crypto trading pair (e.g. BTCUSDT, ETHUSDT, SOLUSDT)",
)

# ─── Data Sources ─────────────────────────────────────────────────────────────
# Streaming push source: computed features arrive via store.push(...) from the
# Feast push service (which consumes the Kafka `computed-features` topic that the
# Flink job produces). The batch_source is the offline fallback for the same view.
stock_push_source = PushSource(
    name="stock_push_source",
    batch_source=FileSource(
        name="stock_features_batch",
        path="/data/features_offline.parquet",
        timestamp_field="computed_at",
    ),
)

# ─── Feature View ─────────────────────────────────────────────────────────────
stock_features_view = FeatureView(
    name="stock_realtime_features",
    entities=[symbol],
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
    description="Features used for real-time crypto direction prediction",
)
