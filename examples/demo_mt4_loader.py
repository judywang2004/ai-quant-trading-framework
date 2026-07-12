from pathlib import Path

from data.mt4_csv_loader import load_mt4_csv


def main():

    candles = load_mt4_csv(
        Path("data/raw/USDJPY_M5.csv"),
        symbol="USDJPY",
        timeframe="M5",
    )

    print()

    print("First candle:")

    print(candles[0])

    print()

    print("Last candle:")

    print(candles[-1])

    print()

    print(f"Total candles: {len(candles)}")


if __name__ == "__main__":
    main()
