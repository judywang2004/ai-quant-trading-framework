from execution.executor_base import ExecutorBase
from models.enums import OrderStatus, SignalType, TradeStatus
from models.order import Order
from models.trade import Trade


class SimulatedExecutor(ExecutorBase):
    """Deterministic MVP executor that fills an order immediately and exits at the take-profit level."""

    def execute(self, order: Order) -> Trade:
        entry_price = order.price
        exit_price = order.signal.take_profit

        if order.signal.signal_type == SignalType.SELL:
            profit = (entry_price - exit_price) * order.volume
        else:
            profit = (exit_price - entry_price) * order.volume

        order.status = OrderStatus.FILLED

        return Trade(
            order=order,
            entry_price=entry_price,
            exit_price=exit_price,
            entry_time=order.timestamp,
            exit_time=order.timestamp,
            profit=profit,
            status=TradeStatus.CLOSED,
        )
