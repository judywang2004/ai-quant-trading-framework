from dataclasses import dataclass
from datetime import datetime

from .order import Order
from .enums import TradeStatus


@dataclass
class Trade:
    order: Order

    entry_price: float
    exit_price: float

    entry_time: datetime
    exit_time: datetime

    profit: float

    status: TradeStatus