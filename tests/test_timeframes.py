import unittest
from datetime import datetime, timedelta

from core.timeframes import (
    candle_close_time,
    is_closed,
    timeframe_duration,
)
from models.candle import Candle


def _candle(timeframe: str, timestamp: datetime) -> Candle:
    return Candle(
        symbol="TEST",
        timeframe=timeframe,
        timestamp=timestamp,
        open=1.0,
        high=1.0,
        low=1.0,
        close=1.0,
        volume=0.0,
    )


def _series(timeframe: str, step: timedelta, count: int) -> list[Candle]:
    start = datetime(2026, 6, 1)
    return [_candle(timeframe, start + step * i) for i in range(count)]


class TimeframeDurationTests(unittest.TestCase):
    def test_known_timeframes(self):
        self.assertEqual(timeframe_duration("M5"), timedelta(minutes=5))
        self.assertEqual(timeframe_duration("M15"), timedelta(minutes=15))
        self.assertEqual(timeframe_duration("H1"), timedelta(hours=1))
        self.assertEqual(timeframe_duration("D1"), timedelta(days=1))

    def test_unknown_timeframe_raises(self):
        with self.assertRaises(ValueError):
            timeframe_duration("W1")


class IsClosedTests(unittest.TestCase):
    def test_candle_closes_one_duration_after_its_open(self):
        for timeframe in ("M5", "M15", "H1", "D1"):
            with self.subTest(timeframe=timeframe):
                opened = datetime(2026, 6, 1, 10, 0)
                candle = _candle(timeframe, opened)
                close = opened + timeframe_duration(timeframe)

                self.assertEqual(candle_close_time(candle), close)
                self.assertFalse(is_closed(candle, opened))
                self.assertFalse(is_closed(candle, close - timedelta(seconds=1)))
                self.assertTrue(is_closed(candle, close))


if __name__ == "__main__":
    unittest.main()
