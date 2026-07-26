"""
Immutable snapshot of everything a pattern detector needs to know about
the market at one point in time, for one symbol/timeframe.

MarketContext is the single source of truth for market *facts*. Every
future detector (HighBaseDetector, PullbackDetector, EMARideDetector,
...) consumes the same MarketContext instance instead of independently
recomputing indicators or re-reading raw OHLC data - this is what keeps
Python backtests, MT4, MT5, and future live execution consistent with
each other.

MarketContext represents facts, never decisions:

    Correct:    ema20 = 154.23, atr = 0.84, daily_assessment.strength = STRONG
    Incorrect:  "buy signal", "high base found", "risk = 0.5%"

Signals, Opportunities, and risk sizing are later pipeline stages built
*from* a MarketContext - none of that belongs here. This module also
does not compute ema20/ema50/atr/daily_assessment itself; it only holds
values that were computed elsewhere (indicators/, DailyTrendAssessment)
and passed in.
"""

from dataclasses import dataclass
from datetime import datetime

from models.candle import Candle
from models.trend_assessment import DailyTrendResult


@dataclass(frozen=True)
class MarketContext:
    symbol: str
    timeframe: str
    timestamp: datetime

    candles: tuple[Candle, ...]

    ema20: float | None = None
    ema50: float | None = None
    atr: float | None = None

    # A short window of previously computed EMA20 values ending at
    # `timestamp` (oldest first), e.g. for a detector to judge slope
    # direction. Supplied by whoever builds the context, same as ema20
    # itself - not computed here.
    ema20_history: tuple[float, ...] = ()

    daily_assessment: DailyTrendResult | None = None

    def __post_init__(self):
        if not isinstance(self.candles, tuple):
            object.__setattr__(self, "candles", tuple(self.candles))

        if not isinstance(self.ema20_history, tuple):
            object.__setattr__(self, "ema20_history", tuple(self.ema20_history))

        if self.atr is not None and self.atr < 0:
            raise ValueError("atr must be non-negative")

    @property
    def latest_candle(self) -> Candle | None:
        """The most recent candle in `candles`, or None if empty."""
        return self.candles[-1] if self.candles else None
