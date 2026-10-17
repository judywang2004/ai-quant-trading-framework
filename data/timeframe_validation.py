"""Check that loaded candles really are the timeframe their file claims."""

from datetime import timedelta

from core.timeframes import timeframe_duration
from models.candle import Candle


def validate_timeframe_spacing(candles: list[Candle], timeframe: str) -> None:
    """
    Raise ValueError if `candles` are not spaced like `timeframe` bars.

    Market closures (weekends, holidays) produce gaps LARGER than one
    bar, so only the smallest gap between consecutive candles is checked:
    it must equal exactly one bar. This catches a file labeled M5 that
    actually holds M15 bars, as well as duplicate or unsorted timestamps.
    """
    if len(candles) < 2:
        return

    expected = timeframe_duration(timeframe)
    gaps = [b.timestamp - a.timestamp for a, b in zip(candles, candles[1:])]
    smallest_gap = min(gaps)

    if smallest_gap <= timedelta(0):
        raise ValueError(
            f"{timeframe} candles contain duplicate or out-of-order timestamps"
        )

    if smallest_gap != expected:
        raise ValueError(
            f"Candles labeled {timeframe} are spaced {smallest_gap} apart "
            f"(expected {expected}); the data does not match its timeframe label"
        )
