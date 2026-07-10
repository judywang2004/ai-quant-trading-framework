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

    def generate_signal(self, candles):
        raise NotImplementedError(
            "TrendPullbackStrategy is not implemented yet."
        )