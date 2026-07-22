from datetime import datetime

from core.market_data import MarketData

from models.signal import Signal
from models.trend_assessment import DailyTrendResult

from .daily_trend_assessment import DailyTrendAssessment
from .strategy_base import Strategy


class TrendPullbackStrategy(Strategy):

    """
    Multi-timeframe trend pullback strategy.

    Planned implementation:

    D1  -> Trend filter
    H1  -> Pullback detection
    M15 -> Setup confirmation
    M5  -> Entry trigger
    """

    def __init__(self, daily_trend_assessment: DailyTrendAssessment | None = None):
        self._daily_trend_assessment = daily_trend_assessment or DailyTrendAssessment()

    @property
    def name(self):
        return "TrendPullbackStrategy"

    def generate_signal(

        self,

        market: MarketData,

        current_index: int,

    ) -> Signal | None:

        # TODO:

        # Implement after Daily/H1/M15/M5 rules are completed.

        return None

    def daily_bias(
        self,
        market: MarketData,
        current_time: datetime,
    ) -> DailyTrendResult:
        """Evaluate the Daily Bias step of the strategy workflow."""
        return self._daily_trend_assessment.assess(market, current_time)
