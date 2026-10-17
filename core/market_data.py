from datetime import datetime

from core.timeframes import is_closed
from models.candle import Candle


class MarketData:
    """
    Historical candles for one symbol across D1/H1/M15/M5.

    Every time-based accessor (`*_at`, `*_history_until`) returns only
    candles that have FULLY CLOSED at the requested time `t` - see
    core/timeframes.py. A candle whose period contains `t` is still
    forming; its high/low/close are not yet known at `t`, so returning it
    would leak future information into a strategy (look-ahead bias).

    Callers that decide "at the close of bar X" must therefore pass X's
    close time (core.timeframes.candle_close_time), not its open
    timestamp.
    """

    def __init__(
        self,
        daily: list[Candle],
        h1: list[Candle],
        m15: list[Candle],
        m5: list[Candle],
    ):
        self.daily = daily
        self.h1 = h1
        self.m15 = m15
        self.m5 = m5

    def __str__(self):

        return (
            f"MarketData("
            f"D1={len(self.daily)}, "
            f"H1={len(self.h1)}, "
            f"M15={len(self.m15)}, "
            f"M5={len(self.m5)})"
        )

    # ------------------------------------------------------------------
    # Latest closed candle at time t
    # ------------------------------------------------------------------

    def daily_at(self, t: datetime) -> Candle | None:
        """Most recent D1 candle that has fully closed at `t`."""
        return _latest_closed(self.daily, t)

    def h1_at(self, t: datetime) -> Candle | None:
        """Most recent H1 candle that has fully closed at `t`."""
        return _latest_closed(self.h1, t)

    def m15_at(self, t: datetime) -> Candle | None:
        """Most recent M15 candle that has fully closed at `t`."""
        return _latest_closed(self.m15, t)

    def m5_at(self, t: datetime) -> Candle | None:
        """Most recent M5 candle that has fully closed at `t`."""
        return _latest_closed(self.m5, t)

    # ------------------------------------------------------------------
    # Closed-candle history up to time t
    # ------------------------------------------------------------------

    def daily_history_until(
        self,
        t: datetime,
        lookback: int | None = None,
    ) -> list[Candle]:
        """D1 candles that have fully closed at `t`, oldest first."""
        return _closed_history(self.daily, t, lookback)

    def h1_history_until(
        self,
        t: datetime,
        lookback: int | None = None,
    ) -> list[Candle]:
        """H1 candles that have fully closed at `t`, oldest first."""
        return _closed_history(self.h1, t, lookback)

    def m15_history_until(
        self,
        t: datetime,
        lookback: int | None = None,
    ) -> list[Candle]:
        """M15 candles that have fully closed at `t`, oldest first."""
        return _closed_history(self.m15, t, lookback)

    def m5_history_until(
        self,
        t: datetime,
        lookback: int | None = None,
    ) -> list[Candle]:
        """M5 candles that have fully closed at `t`, oldest first."""
        return _closed_history(self.m5, t, lookback)


def _closed_history(
    candles: list[Candle],
    t: datetime,
    lookback: int | None,
) -> list[Candle]:

    history = [c for c in candles if is_closed(c, t)]

    if lookback is not None:
        return history[-lookback:]

    return history


def _latest_closed(candles: list[Candle], t: datetime) -> Candle | None:

    for candle in reversed(candles):

        if is_closed(candle, t):
            return candle

    return None
