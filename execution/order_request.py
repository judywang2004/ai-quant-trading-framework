"""
Broker-independent description of an order to be placed.

An OrderRequest is the boundary contract between the framework's
decision-making (strategy / risk / position management) and any
concrete broker integration. It has no dependency on any broker SDK or
API - translating an OrderRequest into real calls (e.g. MT5's
order_send) is the responsibility of a concrete Executor, not this
module. That keeps OrderRequest reusable by both the backtest executor
and a future live executor unchanged.
"""

from dataclasses import dataclass

from models.enums import OrderType, SignalType


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: SignalType       # BUY or SELL
    order_type: OrderType  # MARKET, LIMIT, or STOP

    volume: float          # lot size, e.g. from risk.position_sizer.PositionSizer

    price: float | None = None  # required for LIMIT/STOP; ignored for MARKET
    stop_loss: float | None = None
    take_profit: float | None = None

    comment: str = ""

    def __post_init__(self):
        if self.volume <= 0:
            raise ValueError("volume must be positive")

        if self.order_type != OrderType.MARKET and self.price is None:
            raise ValueError(f"price is required for {self.order_type.value} orders")
