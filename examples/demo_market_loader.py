from data.market_loader import load_market_data


def main():

    market = load_market_data("data/raw")

    print()

    print(market)

    print()

    print("Daily")

    print(market.daily[0])

    print()

    print("H1")

    print(market.h1[0])

    print()

    print("M15")

    print(market.m15[0])

    print()

    print("M5")

    print(market.m5[0])


if __name__ == "__main__":
    main()