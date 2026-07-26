import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime

from core.market_context import MarketContext
from models.candle import Candle
from models.market_bias import MarketBias
from models.trend_assessment import DailyTrendResult, TrendStrength


def _make_candle(close: float, timestamp=datetime(2024, 1, 1)) -> Candle:
    return Candle(
        symbol="USDJPY",
        timeframe="H1",
        timestamp=timestamp,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=0.0,
    )


def _make_daily_assessment(strength: TrendStrength = TrendStrength.STRONG) -> DailyTrendResult:
    return DailyTrendResult(
        bias=MarketBias.BULLISH,
        strength=strength,
        rules=(),
        ema20=154.23,
        ema50=153.10,
        ema20_slope=0.05,
        ema20_slope_status=None,
        ema_separation=1.13,
        ema_separation_pct=0.0074,
        explanation="STRONG bullish daily trend.",
    )


class MarketContextTests(unittest.TestCase):
    def test_is_immutable(self):
        context = MarketContext(
            symbol="USDJPY",
            timeframe="H1",
            timestamp=datetime(2024, 1, 1),
            candles=(_make_candle(150.0),),
        )

        with self.assertRaises(FrozenInstanceError):
            context.symbol = "EURUSD"

    def test_candles_are_normalized_to_a_tuple(self):
        candle_list = [_make_candle(150.0), _make_candle(151.0)]
        context = MarketContext(
            symbol="USDJPY",
            timeframe="H1",
            timestamp=datetime(2024, 1, 1),
            candles=candle_list,
        )

        self.assertIsInstance(context.candles, tuple)
        self.assertEqual(len(context.candles), 2)

        # Mutating the original list afterwards must not affect the context.
        candle_list.append(_make_candle(152.0))
        self.assertEqual(len(context.candles), 2)

    def test_ema20_history_is_normalized_to_a_tuple(self):
        history_list = [101.0, 101.5, 102.0]
        context = MarketContext(
            symbol="USDJPY",
            timeframe="H1",
            timestamp=datetime(2024, 1, 1),
            candles=(_make_candle(150.0),),
            ema20_history=history_list,
        )

        self.assertIsInstance(context.ema20_history, tuple)

        history_list.append(999.0)
        self.assertEqual(len(context.ema20_history), 3)

    def test_defaults_are_none_when_not_supplied(self):
        context = MarketContext(
            symbol="USDJPY",
            timeframe="H1",
            timestamp=datetime(2024, 1, 1),
            candles=(_make_candle(150.0),),
        )

        self.assertIsNone(context.ema20)
        self.assertIsNone(context.ema50)
        self.assertIsNone(context.atr)
        self.assertIsNone(context.daily_assessment)

    def test_stores_supplied_indicator_and_daily_assessment_values(self):
        daily_assessment = _make_daily_assessment()
        context = MarketContext(
            symbol="USDJPY",
            timeframe="H1",
            timestamp=datetime(2024, 1, 1),
            candles=(_make_candle(150.0),),
            ema20=150.5,
            ema50=149.8,
            atr=0.42,
            daily_assessment=daily_assessment,
        )

        self.assertEqual(context.ema20, 150.5)
        self.assertEqual(context.ema50, 149.8)
        self.assertEqual(context.atr, 0.42)
        self.assertIs(context.daily_assessment, daily_assessment)
        self.assertEqual(context.daily_assessment.strength, TrendStrength.STRONG)

    def test_negative_atr_raises(self):
        with self.assertRaises(ValueError):
            MarketContext(
                symbol="USDJPY",
                timeframe="H1",
                timestamp=datetime(2024, 1, 1),
                candles=(_make_candle(150.0),),
                atr=-0.1,
            )

    def test_latest_candle_returns_last_candle(self):
        first = _make_candle(150.0, timestamp=datetime(2024, 1, 1))
        last = _make_candle(151.0, timestamp=datetime(2024, 1, 2))
        context = MarketContext(
            symbol="USDJPY",
            timeframe="H1",
            timestamp=datetime(2024, 1, 2),
            candles=(first, last),
        )

        self.assertIs(context.latest_candle, last)

    def test_latest_candle_is_none_when_no_candles(self):
        context = MarketContext(
            symbol="USDJPY",
            timeframe="H1",
            timestamp=datetime(2024, 1, 1),
            candles=(),
        )

        self.assertIsNone(context.latest_candle)


if __name__ == "__main__":
    unittest.main()
