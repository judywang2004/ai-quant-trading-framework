from pathlib import Path

from core.market_data import MarketData
from data.mt4_csv_loader import load_mt4_csv


def load_market_data(
    data_dir: str | Path,
    symbol: str = "USDJPY",
) -> MarketData:

    data_dir = Path(data_dir)

    daily = load_mt4_csv(
        data_dir / "USDJPY_D1.csv",
        symbol,
        "D1",
    )

    h1 = load_mt4_csv(
        data_dir / "USDJPY_H1.csv",
        symbol,
        "H1",
    )

    m15 = load_mt4_csv(
        data_dir / "USDJPY_M15.csv",
        symbol,
        "M15",
    )

    m5 = load_mt4_csv(
        data_dir / "USDJPY_M5.csv",
        symbol,
        "M5",
    )

    return MarketData(
        daily,
        h1,
        m15,
        m5,
    )