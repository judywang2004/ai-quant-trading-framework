"""
Example usage of the Pattern Framework: build a MarketContext by hand
and run HighBaseDetector against it.

There is no MarketContext-builder component yet (a future task) - this
script assembles one directly from MarketData just to demonstrate the
detect(context) -> Opportunity | None pipeline end to end.
"""

from data.market_loader import load_market_data
from indicators.ema import calculate_ema
from patterns.high_base_detector import HighBaseDetector
from strategies.trend_pullback_strategy import TrendPullbackStrategy
from core.market_context import MarketContext


EMA20_HISTORY_WINDOW = 5


def build_h1_context(market, current_time, strategy) -> MarketContext:
    candles = tuple(c for c in market.h1 if c.timestamp <= current_time)
    closes = [c.close for c in candles]

    ema20_series = calculate_ema(closes, 20) if len(closes) >= 20 else []
    ema50_series = calculate_ema(closes, 50) if len(closes) >= 50 else []

    ema20 = ema20_series[-1] if ema20_series else None
    ema50 = ema50_series[-1] if ema50_series else None
    ema20_history = tuple(ema20_series[-EMA20_HISTORY_WINDOW:])

    daily_assessment = strategy.daily_bias(market, current_time)

    return MarketContext(
        symbol=candles[-1].symbol if candles else "UNKNOWN",
        timeframe="H1",
        timestamp=current_time,
        candles=candles,
        ema20=ema20,
        ema50=ema50,
        ema20_history=ema20_history,
        atr=None,  # no ATR indicator implemented yet
        daily_assessment=daily_assessment,
    )


def main():
    market = load_market_data("data/raw")
    strategy = TrendPullbackStrategy()
    detector = HighBaseDetector()

    current = market.m5[1000]
    context = build_h1_context(market, current.timestamp, strategy)

    print(f"MarketContext: {context.symbol} {context.timeframe} @ {context.timestamp}")
    print(f"Candles available : {len(context.candles)}")
    print(f"EMA20 / EMA50     : {context.ema20} / {context.ema50}")
    print(f"Daily Bias        : {context.daily_assessment.bias.name}")
    print(f"Daily Strength    : {context.daily_assessment.strength.name}")
    print()

    opportunity = detector.detect(context)

    if opportunity is None:
        print("No opportunity detected.")
        return

    print("Opportunity detected:")
    print(opportunity)


if __name__ == "__main__":
    main()
