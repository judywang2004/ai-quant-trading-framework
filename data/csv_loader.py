"""
CSV loader for historical market data.

All loaders should return a list of Candle objects so that
strategies and backtests remain data-source independent.
"""

import csv
from datetime import datetime
from pathlib import Path

from models.candle import Candle


def load_candles(
    csv_file: str | Path,
    symbol: str,
    timeframe: str,
) -> list[Candle]:
    """
    Load historical candles from a CSV file.

    Expected CSV columns:

        timestamp,open,high,low,close,volume

    Example:

        2026-07-01 09:30:00,145.12,145.20,145.05,145.18,1023

    Args:
        csv_file:
            Path to the CSV file.

        symbol:
            Trading symbol (e.g. "USDJPY", "EURUSD", "AAPL").

        timeframe:
            Candle timeframe (e.g. "M5", "H1", "D1").

    Returns:
        A chronologically sorted list of Candle objects.
    """

    csv_path = Path(csv_file)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    candles: list[Candle] = []

    with csv_path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        for row_number, row in enumerate(reader, start=2):
            try:

                candle = Candle(
                    symbol=symbol,
                    timeframe=timeframe,

                    timestamp=datetime.fromisoformat(
                        row["timestamp"]
                    ),

                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )

                candles.append(candle)

            except Exception as ex:
                print(
                    f"Skipping invalid row "
                    f"{row_number}: {ex}"
                )

    candles.sort(
        key=lambda candle: candle.timestamp
    )

    return candles