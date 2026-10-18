from pathlib import Path

from core.market_data import MarketData
from data.mt4_csv_loader import load_mt4_csv
from data.timeframe_validation import validate_timeframe_spacing
from models.candle import Candle


def load_market_data(
    data_dir: str | Path,
    symbol: str = "USDJPY",
) -> MarketData:
    """
    Load `<symbol>_<TF>.csv` MT4 exports for D1, H1, M15 and M5.

    D1, H1 and M15 are required. M5 is optional: if the file is absent,
    MarketData.m5 is empty. Every file is checked against its timeframe
    label (data.timeframe_validation.validate_timeframe_spacing), so a file whose
    bars do not match its name fails loudly instead of silently feeding
    the wrong timeframe into a strategy.
    """

    data_dir = Path(data_dir)

    daily = _load_timeframe(data_dir, symbol, "D1")
    h1 = _load_timeframe(data_dir, symbol, "H1")
    m15 = _load_timeframe(data_dir, symbol, "M15")
    m5 = _load_timeframe(data_dir, symbol, "M5", required=False)

    return MarketData(
        daily,
        h1,
        m15,
        m5,
    )


def _load_timeframe(
    data_dir: Path,
    symbol: str,
    timeframe: str,
    required: bool = True,
) -> list[Candle]:

    csv_file = data_dir / f"{symbol}_{timeframe}.csv"

    if not csv_file.exists():
        if required:
            raise FileNotFoundError(f"Market data file not found: {csv_file}")

        print(f"No {timeframe} data ({csv_file.name} not found); {timeframe} is empty.")
        return []

    candles = load_mt4_csv(csv_file, symbol, timeframe)

    validate_timeframe_spacing(candles, timeframe)

    return candles
