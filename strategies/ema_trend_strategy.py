from models.candle import Candle
from models.signal import Signal
from models.enums import SignalType

from indicators.ema import calculate_ema

from .strategy_base import Strategy


class EMATrendStrategy(Strategy):
    """
    EMA Trend Strategy (Version 1)

    BUY:
        EMA20 > EMA50
        AND Close > EMA20

    SELL:
        EMA20 < EMA50
        AND Close < EMA20
    """

    REQUIRED_HISTORY = 50

    STOP_LOSS = 0.005
    TAKE_PROFIT = 0.010

    def generate_signal(
        self,
        candles: list[Candle],
    ) -> Signal | None:

        if len(candles) < self.REQUIRED_HISTORY:
            return None

        closes = [c.close for c in candles]

        ema20 = calculate_ema(closes, period=20)
        ema50 = calculate_ema(closes, period=50)

        current = candles[-1]

        # BUY
        if ema20[-1] > ema50[-1] and current.close > ema20[-1]:
            return Signal(
                symbol=current.symbol,
                timeframe=current.timeframe,
                timestamp=current.timestamp,
                signal_type=SignalType.BUY,
                strategy_name="EMATrendStrategy",
                entry=current.close,
                stop_loss=current.close - self.STOP_LOSS,
                take_profit=current.close + self.TAKE_PROFIT,
                confidence=0.60,
            )

        # SELL
        if ema20[-1] < ema50[-1] and current.close < ema20[-1]:
            return Signal(
                symbol=current.symbol,
                timeframe=current.timeframe,
                timestamp=current.timestamp,
                signal_type=SignalType.SELL,
                strategy_name="EMATrendStrategy",
                entry=current.close,
                stop_loss=current.close + self.STOP_LOSS,
                take_profit=current.close - self.TAKE_PROFIT,
                confidence=0.60,
            )

        return None