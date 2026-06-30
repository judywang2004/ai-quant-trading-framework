from dataclasses import dataclass
from datetime import datetime

from .signal import Signal
from .enums import OrderStatus
from .enums import OrderType


@dataclass
class Order:
    signal: Signal

    order_type: OrderType

    volume: float

    price: float

    timestamp: datetime

    status: OrderStatus = OrderStatus.PENDING