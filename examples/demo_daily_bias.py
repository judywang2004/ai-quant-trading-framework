from core.timeframes import candle_close_time
from data.market_loader import load_market_data
from strategies.trend_pullback_strategy import TrendPullbackStrategy


def main():

    market = load_market_data("data/raw")

    strategy = TrendPullbackStrategy()

    current = market.m15[1000]

    # Decide at the close of the current M15 candle - the earliest
    # moment its data is known.
    decision_time = candle_close_time(current)

    print()

    print("Current M15")

    print(current.timestamp)

    print(f"Decision time: {decision_time}")

    result = strategy.daily_bias(
        market,
        decision_time,
    )

    print()
    print(result.explanation)


if __name__ == "__main__":
    main()
