from pathlib import Path

from data.csv_loader import load_candles
from data.yfinance_loader import load_yfinance


CSV_FILE = Path("data/historical/USDJPY_M5.csv")


def main():

    if CSV_FILE.exists():

        print("Loading local historical data...")

        candles = load_candles(
            CSV_FILE,
            symbol="USDJPY",
            timeframe="M5",
        )

    else:

        print("Downloading historical data...")

        candles = load_yfinance(
            symbol="JPY=X",
            interval="5m",
            period="60d",
        )

    print(f"Candles: {len(candles)}")

    print(candles[0])
    print(candles[-1])


if __name__ == "__main__":
    main()