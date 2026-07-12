from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from models.candle import Candle


def load_mt4_csv(
    csv_file: str | Path,
    symbol: str,
    timeframe: str,
) -> list[Candle]:
    """
    Load MT4 exported CSV.

    Expected format:

    Date,Time,Open,High,Low,Close,Volume

    Example:

    2026.06.11,11:00,160.535,160.549,160.531,160.544,447
    """

    csv_path = Path(csv_file)

    candles: list[Candle] = []

    with csv_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        reader = csv.reader(f)

        for row in reader:

            if not row:
                continue

            try:

                timestamp = datetime.strptime(
                    row[0] + " " + row[1],
                    "%Y.%m.%d %H:%M",
                )

                candles.append(
                    Candle(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=timestamp,
                        open=float(row[2]),
                        high=float(row[3]),
                        low=float(row[4]),
                        close=float(row[5]),
                        volume=float(row[6]),
                    )
                )

            except Exception as e:

                print(f"Skipping row {row}: {e}")

    print(f"Loaded {len(candles)} {timeframe} candles.")

    return candles