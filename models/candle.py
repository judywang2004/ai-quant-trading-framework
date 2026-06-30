from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Candle:
    symbol: str
    timeframe: str
    timestamp: datetime

    open: float
    high: float
    low: float
    close: float

    volume: float