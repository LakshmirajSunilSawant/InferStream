"""
InferStream — Unit Tests: Binance Live Producer

Covers:
  - StockTick serialization
  - Bid/ask spread validity
  - Serialization edge cases (zero price, large volume)
  - on_message processing (mocked WebSocket + mocked Kafka)
  - Iterative reconnect loop (no recursion), SIGTERM graceful shutdown
"""
import json
import signal
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "producer"))
from main import StockTick, BinanceLiveStreamer


# ── StockTick tests ────────────────────────────────────────────────────────────
class TestStockTick:
    def test_serialize_returns_bytes(self):
        tick = StockTick(
            event_id  = "B-BTCUSDT-1610000000000",
            symbol    = "BTCUSDT",
            price     = 68000.50,
            volume    = 100,
            bid       = 67995.0,
            ask       = 68005.0,
            timestamp = "2026-03-19T12:00:00+00:00",
        )
        data = tick.serialize()
        assert isinstance(data, bytes)
        parsed = json.loads(data)
        assert parsed["symbol"] == "BTCUSDT"
        assert parsed["price"]  == 68000.50

    def test_bid_ask_spread_valid(self):
        tick = StockTick("id", "ETHUSDT", 3500.0, 50, 3499.5, 3500.5, "2026-01-01T00:00:00+00:00")
        assert tick.ask > tick.bid

    def test_source_field_default(self):
        tick = StockTick("id", "SOLUSDT", 150.0, 10, 149.9, 150.1, "2026-01-01T00:00:00+00:00")
        data = json.loads(tick.serialize())
        assert data["source"] == "binance-live"

    def test_serialize_zero_price(self):
        tick = StockTick("id", "BTCUSDT", 0.0, 0, 0.0, 0.0, "2026-01-01T00:00:00+00:00")
        data = json.loads(tick.serialize())
        assert data["price"] == 0.0

    def test_serialize_large_volume(self):
        tick = StockTick("id", "BTCUSDT", 99999.0, 10_000_000, 99998.0, 100000.0, "2026-01-01T00:00:00+00:00")
        data = json.loads(tick.serialize())
        assert data["volume"] == 10_000_000

    def test_timestamp_is_iso_string(self):
        ts = datetime.now(timezone.utc).isoformat()
        tick = StockTick("id", "BTCUSDT", 100.0, 1, 99.9, 100.1, ts)
        data = json.loads(tick.serialize())
        # Must be parseable as ISO 8601
        parsed = datetime.fromisoformat(data["timestamp"])
        assert parsed is not None


# ── BinanceLiveStreamer unit tests ────────────────────────────────────────────
class TestBinanceLiveStreamer:
    @pytest.fixture()
    def streamer(self):
        """Return a streamer with a mocked Kafka producer (no real Kafka)."""
        with patch("main.create_producer") as mock_cp:
            mock_producer = MagicMock()
            mock_cp.return_value = mock_producer
            s = BinanceLiveStreamer()
            s._running = True
            return s

    def test_initial_state(self, streamer):
        assert streamer.sent_count == 0
        assert "BTCUSDT" in streamer.last_prices
        assert streamer._running is True

    def test_on_message_parses_btc(self, streamer):
        """Valid Binance trade payload should produce a Kafka send."""
        payload = {
            "stream": "btcusdt@trade",
            "data": {
                "s": "BTCUSDT",
                "p": "68000.00",
                "q": "0.005",
                "T": 1710000000000,
                "t": 12345678,
            },
        }
        streamer.on_message(None, json.dumps(payload))
        assert streamer.sent_count == 1
        assert streamer.last_prices["BTCUSDT"] == 68000.0
        streamer.producer.send.assert_called_once()

    def test_on_message_skips_missing_data_key(self, streamer):
        """Payload without 'data' key should be silently skipped."""
        streamer.on_message(None, json.dumps({"stream": "btcusdt@bookTicker"}))
        assert streamer.sent_count == 0

    def test_on_message_handles_bad_json(self, streamer):
        """Malformed JSON should not crash the streamer."""
        streamer.on_message(None, "{{not-json}}")
        assert streamer.sent_count == 0

    def test_on_close_does_not_call_start(self, streamer):
        """on_close must NOT call self.start() — that would be recursive."""
        streamer.start = MagicMock()
        streamer.on_close(None, 1000, "Normal close")
        streamer.start.assert_not_called()

    def test_sigterm_sets_running_false(self, streamer):
        """SIGTERM handler must set _running=False."""
        streamer._handle_signal(signal.SIGTERM, None)
        assert streamer._running is False

    def test_on_send_error_logs_error(self, streamer, caplog):
        """Kafka send error callback must log the error."""
        import logging
        with caplog.at_level(logging.ERROR):
            streamer._on_send_error(None, Exception("connection refused"))
        assert "Kafka send error" in caplog.text
