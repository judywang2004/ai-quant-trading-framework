from datetime import datetime

import yfinance as yf

from models.candle import Candle
from zoneinfo import ZoneInfo

def load_yfinance(
    symbol: str,
    interval: str = "5m",
    period: str = "60d",
) -> list[Candle]:
    """
    Download historical market data from Yahoo Finance.

    Returns:
        list[Candle]
    """

    df = yf.download(
        symbol,
        interval=interval,
        period=period,
        progress=False,
    )

    if df.empty:
        return []

    # Flatten MultiIndex columns if necessary
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    candles = []

    for timestamp, row in df.iterrows():
         
       # Convert timezone if available

        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(
                 ZoneInfo("America/New_York")
            )

        candles.append(
            Candle(
                symbol=symbol,
                timeframe=interval.upper(),
                timestamp=timestamp,
                
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),

                volume=float(row["Volume"]),
            )
        )

    return candles