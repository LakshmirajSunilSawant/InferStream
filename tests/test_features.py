"""
InferStream — Unit Tests: Feature Computation

The feature job is a real PyFlink DataStream pipeline; the windowing math was
extracted into pure functions so it stays testable without a Flink cluster.

Covers:
  - Windowed math over the retained tick buffer (avg / vwap / volatility / count)
  - Cutoff eviction: rows older than the window are excluded
  - compute_features: full feature dict + momentum edge cases
  - FeatureProcessFunction side effects (Redis write, batched DuckDB flush)
"""
import os
import sys
import time
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flink_jobs"))
from feature_job import (
    _avg_price,
    _vwap,
    _volatility,
    _count,
    compute_features,
    FeatureProcessFunction,
)

# Rows are (event_ts, price, volume) tuples — the shape held in Flink ListState.
NO_CUTOFF = 0.0


# ── Windowed math ─────────────────────────────────────────────────────────────
class TestWindowMath:
    def test_empty_window_returns_zeros(self):
        assert _avg_price([],  NO_CUTOFF) == 0.0
        assert _vwap([],       NO_CUTOFF) == 0.0
        assert _volatility([], NO_CUTOFF) == 0.0
        assert _count([],      NO_CUTOFF) == 0

    def test_single_element_window(self):
        ts   = time.time()
        rows = [(ts, 100.0, 500)]
        assert _avg_price(rows,  NO_CUTOFF) == 100.0
        assert _vwap(rows,       NO_CUTOFF) == 100.0
        assert _volatility(rows, NO_CUTOFF) == 0.0   # single point → no variance
        assert _count(rows,      NO_CUTOFF) == 1

    def test_count_matches_rows(self):
        ts   = time.time()
        rows = [(ts, 100.0, 1000), (ts + 1, 110.0, 2000)]
        assert _count(rows, NO_CUTOFF) == 2

    def test_avg_price_correct(self):
        ts   = time.time()
        rows = [(ts, 100.0, 1000), (ts + 1, 200.0, 1000)]
        assert abs(_avg_price(rows, NO_CUTOFF) - 150.0) < 1e-9

    def test_vwap_is_volume_weighted(self):
        ts   = time.time()
        # 1000 @ $100  +  2000 @ $200  =>  VWAP = 500000/3000 = $166.67
        rows = [(ts, 100.0, 1000), (ts + 1, 200.0, 2000)]
        expected = (100 * 1000 + 200 * 2000) / 3000
        assert abs(_vwap(rows, NO_CUTOFF) - expected) < 0.01

    def test_vwap_differs_from_mean(self):
        """Guards against vwap silently degrading into a plain average."""
        ts   = time.time()
        rows = [(ts, 100.0, 1), (ts + 1, 200.0, 999)]
        assert _vwap(rows, NO_CUTOFF) > _avg_price(rows, NO_CUTOFF)

    def test_vwap_zero_volume_returns_zero(self):
        ts = time.time()
        assert _vwap([(ts, 100.0, 0)], NO_CUTOFF) == 0.0

    def test_old_ticks_excluded_by_cutoff(self):
        now    = time.time()
        cutoff = now - 5                      # 5-second window
        rows   = [(now - 10, 999.0, 1000),    # stale — outside cutoff
                  (now,      100.0, 500)]     # fresh — retained
        assert _count(rows, cutoff) == 1
        assert abs(_avg_price(rows, cutoff) - 100.0) < 0.01

    def test_row_exactly_at_cutoff_is_retained(self):
        """Filter is `ts >= cutoff`, so the boundary row counts."""
        now  = time.time()
        rows = [(now - 10, 50.0, 100)]
        assert _count(rows, now - 10) == 1
        assert _count(rows, now - 9)  == 0

    def test_volatility_multiple_prices(self):
        ts   = time.time()
        rows = [(ts + i, p, 1000)
                for i, p in enumerate([100.0, 102.0, 98.0, 105.0, 97.0])]
        assert _volatility(rows, NO_CUTOFF) > 0.0

    def test_volatility_constant_price_is_zero(self):
        ts   = time.time()
        rows = [(ts + i, 100.0, 1000) for i in range(10)]
        assert _volatility(rows, NO_CUTOFF) == 0.0


# ── compute_features ──────────────────────────────────────────────────────────
class TestComputeFeatures:
    def _rows(self, now):
        return [(now - 10 + i, 100.0 + i, 1000) for i in range(10)]

    def test_returns_all_feature_keys(self):
        now    = time.time()
        result = compute_features("BTCUSDT", self._rows(now), 105.0, now)
        for key in ("symbol", "avg_price_5m", "momentum_1m", "vwap_10m",
                    "volatility_10m", "trade_count_5m", "current_price",
                    "computed_at"):
            assert key in result

    def test_symbol_is_passed_through(self):
        now = time.time()
        assert compute_features("ETHUSDT", self._rows(now), 105.0, now)["symbol"] == "ETHUSDT"

    def test_momentum_positive_when_price_above_1m_average(self):
        now    = time.time()
        result = compute_features("BTCUSDT", self._rows(now), 500.0, now)
        assert result["momentum_1m"] > 0

    def test_momentum_negative_when_price_below_1m_average(self):
        now    = time.time()
        result = compute_features("BTCUSDT", self._rows(now), 1.0, now)
        assert result["momentum_1m"] < 0

    def test_momentum_zero_when_no_recent_ticks(self):
        """Empty 1m window → avg_1m is 0 → momentum must not divide by zero."""
        now    = time.time()
        stale  = [(now - 5000, 100.0, 1000)]   # older than every window
        result = compute_features("BTCUSDT", stale, 105.0, now)
        assert result["momentum_1m"] == 0.0

    def test_trade_count_counts_only_5m_window(self):
        now  = time.time()
        rows = [(now - 1000, 100.0, 10),   # outside 5m
                (now - 10,   100.0, 10),   # inside
                (now,        100.0, 10)]   # inside
        assert compute_features("BTCUSDT", rows, 100.0, now)["trade_count_5m"] == 2


# ── Operator side effects ─────────────────────────────────────────────────────
class TestRedisWrite:
    def _fn(self, redis_mock):
        fn = FeatureProcessFunction()
        fn.redis = redis_mock
        return fn

    FEATURES = {
        "symbol": "BTCUSDT", "avg_price_5m": 100.0, "momentum_1m": 0.001,
        "vwap_10m": 100.0, "volatility_10m": 0.5, "trade_count_5m": 10,
        "current_price": 101.0, "computed_at": "2026-01-01T00:00:00+00:00",
    }

    def test_hset_called(self):
        r = MagicMock()
        self._fn(r)._write_redis(self.FEATURES)
        r.hset.assert_called_once()

    def test_expire_called(self):
        r = MagicMock()
        self._fn(r)._write_redis(self.FEATURES)
        r.expire.assert_called_once()

    def test_key_is_namespaced_by_symbol(self):
        r = MagicMock()
        self._fn(r)._write_redis(self.FEATURES)
        assert r.hset.call_args[0][0] == "features:BTCUSDT"

    def test_redis_failure_does_not_raise(self):
        r = MagicMock()
        r.hset.side_effect = Exception("connection refused")
        self._fn(r)._write_redis(self.FEATURES)   # must not propagate


class TestDuckDBFlush:
    def _fn(self, conn, ticks=None, feats=None):
        fn = FeatureProcessFunction()
        fn.duckdb         = conn
        fn.tick_buffer    = ticks if ticks is not None else []
        fn.feature_buffer = feats if feats is not None else []
        return fn

    TICK = ["id1", "BTCUSDT", 100.0, 1, 99.9, 100.1, None]
    FEAT = ["BTCUSDT", 100.0, 0.001, 100.0, 0.5, 10, None]

    def test_flush_clears_tick_buffer(self):
        fn = self._fn(MagicMock(), ticks=[self.TICK])
        fn._flush_duckdb()
        assert fn.tick_buffer == []

    def test_flush_clears_feature_buffer(self):
        fn = self._fn(MagicMock(), feats=[self.FEAT])
        fn._flush_duckdb()
        assert fn.feature_buffer == []

    def test_flush_calls_executemany_for_ticks(self):
        conn = MagicMock()
        self._fn(conn, ticks=[self.TICK])._flush_duckdb()
        conn.executemany.assert_called_once()

    def test_flush_empty_buffers_no_db_call(self):
        conn = MagicMock()
        self._fn(conn)._flush_duckdb()
        conn.executemany.assert_not_called()

    def test_flush_handles_duckdb_exception(self):
        """A write error must not propagate — and the buffer still drains."""
        conn = MagicMock()
        conn.executemany.side_effect = Exception("disk full")
        fn = self._fn(conn, ticks=[self.TICK])
        fn._flush_duckdb()                        # must not raise
        assert fn.tick_buffer == []               # no unbounded growth
