from core.timeframes import candle_close_time
from data.market_loader import load_market_data


def main():

    market = load_market_data("data/raw")

    current = market.m15[1006]

    # The latest candle of each timeframe that has fully closed by the
    # close of the current M15 candle.
    decision_time = candle_close_time(current)

    print()

    print("M15")

    print(current)

    print(f"Decision time: {decision_time}")

    print()

    print("Daily (last closed)")

    print(market.daily_at(decision_time))

    print()

    print("H1 (last closed)")

    print(market.h1_at(decision_time))

    print()

    print("M15 (last closed)")

    print(market.m15_at(decision_time))


if __name__ == "__main__":
    main()
