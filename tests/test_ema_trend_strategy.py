import contextlib
import io
import unittest
from datetime import datetime, timedelta

from core.market_data import MarketData
from models.candle import Candle
from models.enums import SignalType
from strategies.ema_trend_strategy import EMATrendStrategy


def _market(closes: list[float]) -> MarketData:
    m5 = [
        Candle(
            symbol="TEST",
            timeframe="M5",
            timestamp=datetime(2026, 6, 1) + timedelta(minutes=5 * i),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=0.0,
        )
        for i, close in enumerate(closes)
    ]
    return MarketData(daily=[], h1=[], m15=[], m5=m5)


def _signal(closes: list[float], index: int | None = None):
    market = _market(closes)
    index = len(closes) - 1 if index is None else index
    # The strategy prints an explanation for every signal; keep test output clean.
    with contextlib.redirect_stdout(io.StringIO()):
        return EMATrendStrategy().generate_signal(market, index)


RISING = [float(i) for i in range(1, 61)]
FALLING = [float(i) for i in range(60, 0, -1)]


class EMATrendStrategyTests(unittest.TestCase):
    def test_can_be_instantiated(self):
        # Regression: generate_signal was marked @abstractmethod.
        self.assertEqual(EMATrendStrategy().name, "EMATrendStrategy")

    def test_insufficient_history_returns_none(self):
        self.assertIsNone(_signal(RISING[:10]))

    def test_uptrend_with_close_above_ema20_returns_buy(self):
        signal = _signal(RISING)

        self.assertEqual(signal.signal_type, SignalType.BUY)
        self.assertLess(signal.stop_loss, signal.entry)
        self.assertGreater(signal.take_profit, signal.entry)

    def test_downtrend_with_close_below_ema20_returns_sell(self):
        signal = _signal(FALLING)

        self.assertEqual(signal.signal_type, SignalType.SELL)
        self.assertGreater(signal.stop_loss, signal.entry)
        self.assertLess(signal.take_profit, signal.entry)

    def test_uptrend_with_close_below_ema20_returns_none(self):
        # Regression: the SELL return was mis-indented and fired whenever
        # the BUY branch did not, including here (EMA20 > EMA50).
        pullback = RISING[:-1] + [45.0]

        self.assertIsNone(_signal(pullback))

    def test_only_candles_up_to_current_index_are_used(self):
        rising_then_crash = RISING + [1.0] * 30

        signal = _signal(rising_then_crash, index=len(RISING) - 1)

        self.assertEqual(signal.signal_type, SignalType.BUY)


if __name__ == "__main__":
    unittest.main()
