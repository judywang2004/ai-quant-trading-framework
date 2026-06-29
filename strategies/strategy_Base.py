from abc import ABC, abstractmethod

from models.candle import Candle
from models.signal import Signal


class Strategy(ABC):

    @abstractmethod
    def generate_signal(self, candle: Candle) -> Signal:
        """Generate a trading signal from a market candle."""
        raise NotImplementedError