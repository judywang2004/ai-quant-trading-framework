from dataclasses import dataclass
from datetime import datetime

from .enums import SignalType


@dataclass(frozen=True)
class Signal:
    symbol: str
    timeframe: str
    timestamp: datetime

    signal_type: SignalType

    strategy_name: str

    entry: float
    stop_loss: float
    take_profit: float

    confidence: float = 0.5