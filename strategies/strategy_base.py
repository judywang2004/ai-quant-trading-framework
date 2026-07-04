from abc import ABC, abstractmethod

from models.candle import Candle
from models.signal import Signal


class Strategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the strategy."""
        raise NotImplementedError


    @abstractmethod
    def generate_signal(
        self,
        candles: list[Candle],
    ) -> Signal | None:
        """
        Generate a trading signal from historical market data.

        Returns:
            Signal if a trade should be taken.
            None if no trade exists.
        """
        raise NotImplementedError