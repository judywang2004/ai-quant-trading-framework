from data.market_loader import load_market_data


def main():

    market = load_market_data("data/raw")

    current = market.m5[1006]

    print()

    print("M5")

    print(current)

    print()

    print("Daily")

    print(market.daily_at(current.timestamp))

    print()

    print("H1")

    print(market.h1_at(current.timestamp))

    print()

    print("M15")

    print(market.m15_at(current.timestamp))


if __name__ == "__main__":
    main()