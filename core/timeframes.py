"""Timeframe durations and the closed-candle rule.

A Candle's `timestamp` is its OPEN time (MT4/MT5/TradingView
convention). A candle is only complete - and therefore only safe for a
strategy to read - once its full duration has elapsed:

    candle is closed at time t  <=>  candle.timestamp + duration <= t

Every multi-timeframe access in MarketData goes through `is_closed`, so
no strategy can see a candle's high/low/close before that candle has
finished forming (look-ahead bias).
"""

from datetime import datetime, timedelta

from models.candle import Candle

TIMEFRAME_DURATIONS: dict[str, timedelta] = {
    "M1": timedelta(minutes=1),
    "M5": timedelta(minutes=5),
    "M15": timedelta(minutes=15),
    "M30": timedelta(minutes=30),
    "H1": timedelta(hours=1),
    "H4": timedelta(hours=4),
    "D1": timedelta(days=1),
}


def timeframe_duration(timeframe: str) -> timedelta:
    """Return the duration of one candle of `timeframe` (e.g. "H1")."""
    try:
        return TIMEFRAME_DURATIONS[timeframe.upper()]
    except KeyError:
        raise ValueError(f"Unknown timeframe: {timeframe!r}") from None


def candle_close_time(candle: Candle) -> datetime:
    """The moment `candle` finishes forming (open time + duration)."""
    return candle.timestamp + timeframe_duration(candle.timeframe)


def is_closed(candle: Candle, t: datetime) -> bool:
    """True if `candle` has fully closed at time `t`."""
    return candle_close_time(candle) <= t

