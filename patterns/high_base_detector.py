"""
HighBaseDetector V1 - production rules.

Implements Rules HB-001 through HB-007 of the High Base specification.
Every check below is traceable to exactly one rule ID via its method
name and inline comments - see `detect()` for the full rule sequence.

Consumes only MarketContext; never mutates it, never calculates an
indicator (EMA/ATR) itself, never sizes risk, never talks to a broker.
The only indicator-derived values used - ema20, ema50, and a short
ema20_history for the slope check - are read directly off MarketContext
as already-supplied facts, not computed here. HB-004/HB-005/HB-006
instead work directly off raw OHLC (context.candles): recognizing
market structure (an impulse leg, a tight range, a breakout close) is
exactly what a pattern detector is for.
"""

from core.market_context import MarketContext
from core.opportunity import Opportunity, OpportunityType, PatternState
from models.candle import Candle
from models.trend_assessment import TrendStrength

# --- HB-004: Impulse Leg --------------------------------------------
# Candles, immediately preceding the base window, inspected for a
# "meaningful bullish move".
IMPULSE_LOOKBACK = 5
# V1 heuristic (see _passes_hb004_impulse_leg): net % gain from the
# first to the last close across IMPULSE_LOOKBACK candles must be at
# least this. Future versions may replace this with a proper impulse
# measure (e.g. ATR-normalized range).
IMPULSE_MIN_GAIN_PCT = 0.01

# --- HB-005: High Base ------------------------------------------------
# Candles, immediately preceding the breakout candle, evaluated as the
# consolidation itself.
BASE_LOOKBACK = 10
# Floor: fewer candles than this in the base window is insufficient
# data to call it a base, even if BASE_LOOKBACK is configured higher.
MIN_BASE_CANDLES = 5
# Consolidation (high - low) / low must not exceed this fraction of
# price. Expressed as a percentage of price, not raw price units, so
# the same default is meaningful across instruments (see
# DailyTrendAssessment for the same convention).
MAX_BASE_RANGE_PCT = 0.01

# --- HB-006: Breakout ---------------------------------------------------
# Extra % above the base high required for a close to count as a
# breakout, to filter out marginal/noise breaks. 0.0 = any close above
# the base high qualifies.
BREAKOUT_BUFFER_PCT = 0.0


class HighBaseDetector:
    """High Base pattern detector. See rule IDs HB-001..HB-007."""

    NAME = "HighBaseDetector"

    def __init__(
        self,
        impulse_lookback: int = IMPULSE_LOOKBACK,
        impulse_min_gain_pct: float = IMPULSE_MIN_GAIN_PCT,
        base_lookback: int = BASE_LOOKBACK,
        min_base_candles: int = MIN_BASE_CANDLES,
        max_base_range_pct: float = MAX_BASE_RANGE_PCT,
        breakout_buffer_pct: float = BREAKOUT_BUFFER_PCT,
    ):
        if impulse_lookback < 1:
            raise ValueError("impulse_lookback must be at least 1")

        if base_lookback < 1:
            raise ValueError("base_lookback must be at least 1")

        if not 1 <= min_base_candles <= base_lookback:
            raise ValueError("min_base_candles must be between 1 and base_lookback")

        self.impulse_lookback = impulse_lookback
        self.impulse_min_gain_pct = impulse_min_gain_pct
        self.base_lookback = base_lookback
        self.min_base_candles = min_base_candles
        self.max_base_range_pct = max_base_range_pct
        self.breakout_buffer_pct = breakout_buffer_pct

    def detect(self, context: MarketContext) -> Opportunity | None:
        if not self._passes_hb001_daily_trend_strong(context):
            return None

        if not self._passes_hb002_ema_alignment(context):
            return None

        if not self._passes_hb003_ema20_rising(context):
            return None

        base_candles = self._base_candles(context)
        if base_candles is None:
            return None  # insufficient data to evaluate HB-004/HB-005

        if not self._passes_hb004_impulse_leg(context, base_candles):
            return None

        base_high, base_low = self._base_range(base_candles)
        if not self._passes_hb005_high_base(base_high, base_low):
            return None

        breakout_candle = context.latest_candle
        if not self._passes_hb006_breakout(breakout_candle, base_high):
            return None

        return self._build_opportunity_hb007(context, breakout_candle, base_high, base_low)

    # ------------------------------------------------------------------
    # HB-001: Daily Trend must be STRONG
    # ------------------------------------------------------------------

    def _passes_hb001_daily_trend_strong(self, context: MarketContext) -> bool:
        assessment = context.daily_assessment
        return assessment is not None and assessment.strength == TrendStrength.STRONG

    # ------------------------------------------------------------------
    # HB-002: EMA Alignment (EMA20 > EMA50)
    # ------------------------------------------------------------------

    def _passes_hb002_ema_alignment(self, context: MarketContext) -> bool:
        return (
            context.ema20 is not None
            and context.ema50 is not None
            and context.ema20 > context.ema50
        )

    # ------------------------------------------------------------------
    # HB-003: EMA20 Slope (must be rising)
    # ------------------------------------------------------------------

    def _passes_hb003_ema20_rising(self, context: MarketContext) -> bool:
        history = context.ema20_history
        if len(history) < 2:
            return False

        # V1: simple direction check (last value above first value).
        # Future versions may replace this with a regression slope or a
        # slope normalized against price/ATR.
        return history[-1] > history[0]

    # ------------------------------------------------------------------
    # Windowing shared by HB-004 / HB-005 / HB-006
    # ------------------------------------------------------------------

    def _base_candles(self, context: MarketContext) -> tuple[Candle, ...] | None:
        candles = context.candles
        if len(candles) < self.min_base_candles + 1:  # +1 for the breakout candle
            return None

        window = candles[-(self.base_lookback + 1):-1]
        if len(window) < self.min_base_candles:
            return None

        return window

    def _impulse_candles(
        self, context: MarketContext, base_candles: tuple[Candle, ...]
    ) -> tuple[Candle, ...] | None:
        candles = context.candles
        base_start_index = len(candles) - 1 - len(base_candles)
        impulse_start = base_start_index - self.impulse_lookback

        if impulse_start < 0:
            return None

        return candles[impulse_start:base_start_index]

    # ------------------------------------------------------------------
    # HB-004: Impulse Leg
    # ------------------------------------------------------------------

    def _passes_hb004_impulse_leg(
        self, context: MarketContext, base_candles: tuple[Candle, ...]
    ) -> bool:
        impulse_candles = self._impulse_candles(context, base_candles)
        if not impulse_candles:
            return False

        start_close = impulse_candles[0].close
        end_close = impulse_candles[-1].close
        if start_close <= 0:
            return False

        # V1 heuristic: net % price change from the first to the last
        # close across the impulse window. A real impulse leg should
        # show a clear net gain over that window; this does not check
        # monotonicity or measure the move candle-by-candle.
        gain_pct = (end_close - start_close) / start_close
        return gain_pct >= self.impulse_min_gain_pct

    # ------------------------------------------------------------------
    # HB-005: High Base
    # ------------------------------------------------------------------

    def _base_range(self, base_candles: tuple[Candle, ...]) -> tuple[float, float]:
        base_high = max(c.high for c in base_candles)
        base_low = min(c.low for c in base_candles)
        return base_high, base_low

    def _passes_hb005_high_base(self, base_high: float, base_low: float) -> bool:
        if base_low <= 0:
            return False

        range_pct = (base_high - base_low) / base_low
        return range_pct <= self.max_base_range_pct

    # ------------------------------------------------------------------
    # HB-006: Breakout (close-based confirmation only, no intrabar)
    # ------------------------------------------------------------------

    def _passes_hb006_breakout(self, breakout_candle: Candle, base_high: float) -> bool:
        required_close = base_high * (1 + self.breakout_buffer_pct)
        return breakout_candle.close > required_close

    # ------------------------------------------------------------------
    # HB-007: Opportunity
    # ------------------------------------------------------------------

    def _build_opportunity_hb007(
        self,
        context: MarketContext,
        breakout_candle: Candle,
        base_high: float,
        base_low: float,
    ) -> Opportunity:
        return Opportunity(
            symbol=context.symbol,
            timeframe=context.timeframe,
            timestamp=context.timestamp,
            opportunity_type=OpportunityType.HIGH_BASE,
            state=PatternState.READY,
            bias=context.daily_assessment.bias,
            entry_price=breakout_candle.close,
            stop_price=base_low,
            strategy_name=self.NAME,
            quality=5,
            confidence=1.0,
            notes=(
                f"High Base breakout: base range {base_low:.5f}-{base_high:.5f}, "
                f"breakout close {breakout_candle.close:.5f}."
            ),
        )
