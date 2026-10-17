from core.timeframes import candle_close_time
from data.market_loader import load_market_data


def main():

    market = load_market_data("data/raw")

    current = market.m15[1000]

    # Only candles that have fully closed by the close of the current
    # M15 candle are returned.
    decision_time = candle_close_time(current)

    print("Current M15")
    print(current)
    print(f"Decision time: {decision_time}")

    daily = market.daily_history_until(
        decision_time,
        lookback=5,
    )

    print("\nLast 5 closed Daily Candles")

    for c in daily:
        print(c.timestamp, c.close)

    h1 = market.h1_history_until(
        decision_time,
        lookback=5,
    )

    print("\nLast 5 closed H1 Candles")

    for c in h1:
        print(c.timestamp, c.close)

    m15 = market.m15_history_until(
        decision_time,
        lookback=5,
    )

    print("\nLast 5 closed M15 Candles")

    for c in m15:
        print(c.timestamp, c.close)


if __name__ == "__main__":
    main()
