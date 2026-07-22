from data.market_loader import load_market_data
from strategies.trend_pullback_strategy import TrendPullbackStrategy


def main():

    market = load_market_data("data/raw")

    strategy = TrendPullbackStrategy()

    current = market.m5[1000]

    print()

    print("Current M5")

    print(current.timestamp)

    result = strategy.daily_bias(
        market,
        current.timestamp,
    )

    print()
    print(result.explanation)


if __name__ == "__main__":
    main()
