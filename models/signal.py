# A strategy creates a signal.
# BUY EURUSD
#Entry = 1.1250
#SL = 1.1200
#TP = 1.1350
#Confidence = 0.82
##

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Signal:
    symbol: str
    timeframe: str
    timestamp: datetime

    signal_type: SignalType

    entry: float
    stop_loss: float
    take_profit: float

    confidence: float = 1.0