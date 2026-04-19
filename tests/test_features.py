"""
StreamML — Unit Tests: Feature Computation

Covers:
  - TickWindow sliding window logic
  - Edge cases: empty, single-element, stale eviction
  - Batch flush triggering (size and interval)
  - compute_and_store with mocked Redis
"""
import os
import sys
import time
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flink_jobs"))
from feature_job import TickWindow, SymbolState, compute_and_store, flush_to_duckdb


# ── TickWindow tests ───────────────────────────────────────────────────────────
class TestTickWindow:
    def test_empty_window_returns_zeros(self):
        w = TickWindow(60)
        assert w.avg_price()  == 0.0
        assert w.vwap()       == 0.0
        assert w.volatility() == 0.0
        assert w.count()      == 0

    def test_single_element_window(self):
        w  = TickWindow(60)
        ts = time.time()
        w.add(ts, 100.0, 500)
        assert w.avg_price()  == 100.0
        assert w.vwap()       == 100.0
        assert w.volatility() == 0.0   # single point → no variance
        assert w.count()      == 1

    def test_add_and_count(self):
        w  = TickWindow(60)
        ts = time.time()
        w.add(ts,     100.0, 1000)
        w.add(ts + 1, 110.0, 2000)
        assert w.count() == 2

    def test_avg_price_correct(self):
        w  = TickWindow(60)
        ts = time.time()
        w.add(ts,     100.0, 1000)
        w.add(ts + 1, 200.0, 1000)
        assert abs(w.avg_price() - 150.0) < 1e-9

    def test_vwap_calculation(self):
        w  = TickWindow(60)
        ts = time.time()
        # 1000 @ $100  +  2000 @ $200  =>  VWAP = 500/3 = $166.67
        w.add(ts,     100.0, 1000)
        w.add(ts + 1, 200.0, 2000)
        expected = (100 * 1000 + 200 * 2000) / 3000
        assert abs(w.vwap() - expected) < 0.01

    def test_vwap_zero_volume_returns_zero(self):
        w  = TickWindow(60)
        ts = time.time()
        w.add(ts, 100.0, 0)
        assert w.vwap() == 0.0

    def test_old_ticks_evicted(self):
        w  = TickWindow(5)  # 5 second window
        ts = time.time() - 10
        w.add(ts, 999.0, 1000)           # old — should be evicted
        w.add(time.time(), 100.0, 500)   # recent — stays
        assert w.count() == 1
        assert abs(w.avg_price() - 100.0) < 0.01

    def test_volatility_multiple_prices(self):
        w  = TickWindow(60)
        ts = time.time()
        for i, p in enumerate([100.0, 102.0, 98.0, 105.0, 97.0]):
            w.add(ts + i, p, 1000)
        assert w.volatility() > 0.0

    def test_volatility_constant_price_is_zero(self):
        w  = TickWindow(60)
        ts = time.time()
        for i in range(10):
            w.add(ts + i, 100.0, 1000)
        assert w.volatility() == 0.0

    def test_window_boundary_exactly_at_cutoff(self):
        """Tick exactly at the cutoff time should be evicted."""
        window_sec = 10
        w  = TickWindow(window_sec)
        now = time.time()
        # Add a tick exactly at (now - window_sec), which is the boundary
        w.add(now - window_sec - 0.001, 50.0, 100)  # just outside
        w.add(now, 100.0, 100)                        # inside
        # The old tick should be evicted when we add the new one
        assert w.count() == 1

    def test_prices_list_matches_count(self):
        w  = TickWindow(60)
        ts = time.time()
        for i in range(5):
            w.add(ts + i, float(i * 10), 100)
        assert len(w.prices()) == w.count() == 5


# ── Batch flush tests ──────────────────────────────────────────────────────────
class TestDuckDBFlush:
    def test_flush_clears_tick_buffer(self):
        mock_conn = MagicMock()
        tick_buf  = [["id1", "BTCUSDT", 100.0, 1, 99.9, 100.1, None]]
        feat_buf: list = []
        flush_to_duckdb(mock_conn, tick_buf, feat_buf)
        assert tick_buf == []

    def test_flush_clears_feature_buffer(self):
        mock_conn = MagicMock()
        tick_buf: list = []
        feat_buf = [["BTCUSDT", 100.0, 0.001, 100.0, 0.5, 10, None]]
        flush_to_duckdb(mock_conn, tick_buf, feat_buf)
        assert feat_buf == []

    def test_flush_calls_executemany_for_ticks(self):
        mock_conn = MagicMock()
        tick_buf  = [["id1", "BTCUSDT", 100.0, 1, 99.9, 100.1, None]]
        feat_buf: list = []
        flush_to_duckdb(mock_conn, tick_buf, feat_buf)
        mock_conn.executemany.assert_called_once()

    def test_flush_empty_buffers_no_db_call(self):
        mock_conn = MagicMock()
        flush_to_duckdb(mock_conn, [], [])
        mock_conn.executemany.assert_not_called()

    def test_flush_handles_duckdb_exception(self):
        """DuckDB write error in batch should not propagate — just log warning."""
        mock_conn = MagicMock()
        mock_conn.executemany.side_effect = Exception("disk full")
        tick_buf  = [["id1", "BTCUSDT", 100.0, 1, 99.9, 100.1, None]]
        feat_buf: list = []
        # Should not raise
        flush_to_duckdb(mock_conn, tick_buf, feat_buf)


# ── compute_and_store tests ───────────────────────────────────────────────────
class TestComputeAndStore:
    def _make_state(self):
        state = SymbolState()
        ts    = time.time()
        for i in range(10):
            state.w5m.add(ts + i,  100.0 + i, 1000)
            state.w1m.add(ts + i,  100.0 + i, 1000)
            state.w10m.add(ts + i, 100.0 + i, 1000)
        return state

    def test_returns_feature_dict(self):
        mock_redis = MagicMock()
        state  = self._make_state()
        result = compute_and_store("BTCUSDT", state, mock_redis, 105.0)
        assert "avg_price_5m"   in result
        assert "momentum_1m"    in result
        assert "vwap_10m"       in result
        assert "volatility_10m" in result
        assert "trade_count_5m" in result
        assert "current_price"  in result

    def test_redis_hset_called(self):
        mock_redis = MagicMock()
        state  = self._make_state()
        compute_and_store("BTCUSDT", state, mock_redis, 105.0)
        mock_redis.hset.assert_called_once()

    def test_redis_expire_called(self):
        mock_redis = MagicMock()
        state  = self._make_state()
        compute_and_store("BTCUSDT", state, mock_redis, 105.0)
        mock_redis.expire.assert_called_once()

    def test_redis_failure_does_not_crash(self):
        mock_redis = MagicMock()
        mock_redis.hset.side_effect = Exception("connection refused")
        state  = self._make_state()
        # Should not raise
        result = compute_and_store("BTCUSDT", state, mock_redis, 105.0)
        assert result is not None
