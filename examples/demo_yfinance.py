from pathlib import Path
import csv

from data.yfinance_loader import load_yfinance


OUTPUT_FILE = Path("data/historical/USDJPY_M5.csv")


def main():

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    candles = load_yfinance(
        symbol="JPY=X",
        interval="5m",
        period="60d",
    )

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow([
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ])

        for candle in candles:

            writer.writerow([
                candle.timestamp.isoformat(),
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.volume,
            ])

    print(f"Downloaded {len(candles)} candles")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()