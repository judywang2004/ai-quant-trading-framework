from abc import ABC, abstractmethod

from models.order import Order
from models.trade import Trade


class ExecutorBase(ABC):
    """Abstract base class for all trade executors."""

    @abstractmethod
    def execute(self, order: Order) -> Trade:
        """Execute an order and return the resulting trade."""
        raise NotImplementedError