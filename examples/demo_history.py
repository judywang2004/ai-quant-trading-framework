from data.market_loader import load_market_data


def main():

    market = load_market_data("data/raw")

    current = market.m5[1000]

    print("Current M5")
    print(current)

    daily = market.daily_history_until(
        current.timestamp,
        lookback=5,
    )

    print("\nLast 5 Daily Candles")

    for c in daily:
        print(c.timestamp, c.close)

    h1 = market.h1_history_until(
        current.timestamp,
        lookback=5,
    )

    print("\nLast 5 H1 Candles")

    for c in h1:
        print(c.timestamp, c.close)

    m15 = market.m15_history_until(
        current.timestamp,
        lookback=5,
    )

    print("\nLast 5 M15 Candles")

    for c in m15:
        print(c.timestamp, c.close)


if __name__ == "__main__":
    main()