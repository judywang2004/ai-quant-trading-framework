from models.candle import Candle
from models.signal import Signal
from models.enums import SignalType

from .strategy_base import Strategy


class DummyStrategy(Strategy):

    @property
    def name(self) -> str:
        return "DummyStrategy"

    def generate_signal(self, candles: list[Candle]) -> Signal | None:
        """Generate a signal using the latest candle."""

        if not candles:
            return None

        candle = candles[-1]

        if candle.close > candle.open:
            signal_type = SignalType.BUY
            stop_loss = candle.close - 0.005
            take_profit = candle.close + 0.010
        else:
            signal_type = SignalType.SELL
            stop_loss = candle.close + 0.005
            take_profit = candle.close - 0.010

        return Signal(
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            timestamp=candle.timestamp,
            signal_type=signal_type,
            strategy_name="DummyStrategy",
            entry=candle.close,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=0.5,
        )