import unittest
from datetime import datetime, timedelta

from data.timeframe_validation import validate_timeframe_spacing
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


class ValidateTimeframeSpacingTests(unittest.TestCase):
    def test_correctly_spaced_data_passes(self):
        self.assertIsNone(validate_timeframe_spacing(_series("M15", timedelta(minutes=15), 10), "M15"))

    def test_weekend_gaps_are_allowed(self):
        candles = _series("H1", timedelta(hours=1), 5)
        candles.append(_candle("H1", candles[-1].timestamp + timedelta(hours=50)))

        self.assertIsNone(validate_timeframe_spacing(candles, "H1"))

    def test_m15_bars_labeled_m5_are_rejected(self):
        # Regression: data/raw/USDJPY_M5.csv held M15 bars.
        mislabeled = _series("M5", timedelta(minutes=15), 10)

        with self.assertRaisesRegex(ValueError, "does not match its timeframe label"):
            validate_timeframe_spacing(mislabeled, "M5")

    def test_duplicate_timestamps_are_rejected(self):
        candles = _series("M5", timedelta(minutes=5), 5)
        candles.append(candles[-1])

        with self.assertRaisesRegex(ValueError, "duplicate or out-of-order"):
            validate_timeframe_spacing(candles, "M5")


if __name__ == "__main__":
    unittest.main()
