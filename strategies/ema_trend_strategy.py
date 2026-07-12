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
    # TODO:
    # Replace fixed offsets with ATR-based stop.
    STOP_LOSS = 0.005
    TAKE_PROFIT = 0.010

    @property
    def name(self) -> str:
        return "EMATrendStrategy"

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
        ema20_value = ema20[-1]
        ema50_value = ema50[-1]

        # BUY
        # BUY

        if ema20_value > ema50_value and current.close > ema20_value:

            print(f"""

        ========== SIGNAL ==========

        Time   : {current.timestamp}

        EMA20  : {ema20_value:.3f}

        EMA50  : {ema50_value:.3f}

        Close  : {current.close:.3f}

        Decision : BUY

        Reason:

        ✓ EMA20 > EMA50

        ✓ Close > EMA20

        ============================
         """) 
            
            return Signal(
                symbol=current.symbol,
                timeframe=current.timeframe,
                timestamp=current.timestamp,
                signal_type=SignalType.BUY,
                strategy_name=self.name,
                entry=current.close,
                stop_loss=current.close - self.STOP_LOSS,
                take_profit=current.close + self.TAKE_PROFIT,
                confidence=0.60,
            )

        # SELL
        if ema20_value < ema50_value and current.close < ema20_value:

            print(f"""

        ========== SIGNAL ==========

        Time   : {current.timestamp}

        EMA20  : {ema20_value:.3f}

        EMA50  : {ema50_value:.3f}

        Close  : {current.close:.3f}

        Decision : SELL

        Reason:

        ✓ EMA20 < EMA50

        ✓ Close < EMA20

        ============================

        """)
        return Signal(
                symbol=current.symbol,
                timeframe=current.timeframe,
                timestamp=current.timestamp,
                signal_type=SignalType.SELL,
                strategy_name=self.name,
                entry=current.close,
                stop_loss=current.close + self.STOP_LOSS,
                take_profit=current.close - self.TAKE_PROFIT,
                confidence=0.60,
            )

        return None