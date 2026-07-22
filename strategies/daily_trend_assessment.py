"""DailyTrendAssessment: evaluates the Daily Bias step of the workflow.

See CLAUDE.md, "Current Trading Rules" -> Daily Bias.

Design note (V2): the Daily timeframe has exactly one job - decide
whether the market is currently in a healthy bullish trend worth looking
for long opportunities on lower timeframes. It does not find entries,
pullbacks, or generate signals; those belong to lower-timeframe
components that consume this result.
"""

from datetime import datetime

from core.constants import (
    DAILY_EMA_FAST_PERIOD,
    DAILY_EMA_SLOW_PERIOD,
    DAILY_MARKET_STRUCTURE_LOOKBACK,
    DAILY_TREND_FLAT_SLOPE_THRESHOLD_PCT,
    DAILY_TREND_HISTORY_LOOKBACK,
    DAILY_TREND_MIN_EMA_SEPARATION_PCT,
    DAILY_TREND_MIN_HISTORY,
    DAILY_TREND_SLOPE_LOOKBACK,
)
from core.market_data import MarketData
from indicators.ema import calculate_ema
from models.candle import Candle
from models.market_bias import MarketBias
from models.trend_assessment import (
    DailyTrendResult,
    RuleResult,
    SlopeStatus,
    TrendStrength,
)


class DailyTrendAssessment:
    """
    Evaluates the Daily Bias for a single point in time, using only
    completed daily candles (candles with timestamp <= current_time).

    Rules evaluated:
        1. EMA Alignment  - EMA20 > EMA50. Required. Determines whether
                             there is a bullish trend at all.
        2. EMA20 Rising   - classifies the EMA20 slope over
                             `slope_lookback` completed candles as
                             Rising / Flat / Falling.
        3. EMA Separation - |EMA20 - EMA50| as a percentage of EMA50 must
                             be >= `min_ema_separation_pct`. Confirms the
                             trend has not lost quality.
        4. Market Structure - placeholder. Not implemented; see
                             `evaluate_market_structure`.

    Classification:
        NONE   - alignment failed, OR EMA20 is falling.
        STRONG - alignment passed, EMA20 is rising, AND separation is
                 sufficient.
        WEAK   - alignment passed and EMA20 is not falling, but EMA20 is
                 only flat (not clearly rising) and/or separation is
                 below the configured minimum.

    `bias` mirrors `strength`: BULLISH whenever strength is WEAK or
    STRONG, NEUTRAL whenever strength is NONE. This keeps the two fields
    consistent - callers that only check `bias == MarketBias.BULLISH`
    never see a "bullish" result that this component itself considers
    unhealthy.

    Rule 4 is a placeholder hook (`evaluate_market_structure`) that
    always reports NOT_IMPLEMENTED and never influences bias/strength.
    Implementing it later only means changing that one method's body -
    the public `assess()` signature and the shape of `DailyTrendResult`
    do not need to change.
    """

    RULE_EMA_ALIGNMENT = "ema_alignment"
    RULE_EMA_SLOPE = "ema20_slope"
    RULE_EMA_SEPARATION = "ema_separation"
    RULE_MARKET_STRUCTURE = "market_structure"

    def __init__(
        self,
        fast_period: int = DAILY_EMA_FAST_PERIOD,
        slow_period: int = DAILY_EMA_SLOW_PERIOD,
        slope_lookback: int = DAILY_TREND_SLOPE_LOOKBACK,
        flat_slope_threshold_pct: float = DAILY_TREND_FLAT_SLOPE_THRESHOLD_PCT,
        min_ema_separation_pct: float = DAILY_TREND_MIN_EMA_SEPARATION_PCT,
        min_history: int = DAILY_TREND_MIN_HISTORY,
        history_lookback: int = DAILY_TREND_HISTORY_LOOKBACK,
        market_structure_lookback: int = DAILY_MARKET_STRUCTURE_LOOKBACK,
    ):
        if slope_lookback < 2:
            raise ValueError("slope_lookback must be at least 2")

        self.fast_period = fast_period
        self.slow_period = slow_period
        self.slope_lookback = slope_lookback
        self.flat_slope_threshold_pct = flat_slope_threshold_pct
        self.min_ema_separation_pct = min_ema_separation_pct
        self.min_history = min_history
        self.history_lookback = history_lookback
        self.market_structure_lookback = market_structure_lookback

    def assess(self, market: MarketData, current_time: datetime) -> DailyTrendResult:
        history = market.daily_history_until(
            current_time,
            lookback=self.history_lookback,
        )

        if len(history) < self.min_history or len(history) < self.slope_lookback:
            return self._insufficient_history_result(len(history))

        closes = [c.close for c in history]
        ema20_values = calculate_ema(closes, self.fast_period)
        ema50_values = calculate_ema(closes, self.slow_period)

        ema20 = ema20_values[-1]
        ema50 = ema50_values[-1]

        slope, slope_pct, slope_status = self._evaluate_slope(ema20_values)
        separation, separation_pct, separation_ok = self._evaluate_separation(
            ema20, ema50
        )

        alignment_rule = self._build_alignment_rule(ema20, ema50)
        slope_rule = self._build_slope_rule(slope, slope_pct, slope_status)
        separation_rule = self._build_separation_rule(
            separation, separation_pct, separation_ok
        )
        market_structure_rule = self.evaluate_market_structure(history)

        bias, strength = self._classify(
            alignment_passed=alignment_rule.passed,
            slope_status=slope_status,
            separation_ok=separation_ok,
        )

        rules = (alignment_rule, slope_rule, separation_rule, market_structure_rule)

        return DailyTrendResult(
            bias=bias,
            strength=strength,
            rules=rules,
            ema20=ema20,
            ema50=ema50,
            ema20_slope=slope,
            ema20_slope_status=slope_status,
            ema_separation=separation,
            ema_separation_pct=separation_pct,
            explanation=self._build_explanation(
                candle=history[-1],
                ema20=ema20,
                ema50=ema50,
                slope=slope,
                separation=separation,
                bias=bias,
                strength=strength,
                rules=rules,
                slope_status=slope_status,
                separation_ok=separation_ok,
            ),
        )

    # ------------------------------------------------------------------
    # Rule 2: EMA20 Rising
    # ------------------------------------------------------------------

    def _evaluate_slope(
        self, ema20_values: list[float]
    ) -> tuple[float, float, SlopeStatus]:
        window = ema20_values[-self.slope_lookback:]
        slope = (window[-1] - window[0]) / (len(window) - 1)
        slope_pct = slope / window[-1] if window[-1] else 0.0

        if slope_pct > self.flat_slope_threshold_pct:
            status = SlopeStatus.RISING
        elif slope_pct < -self.flat_slope_threshold_pct:
            status = SlopeStatus.FALLING
        else:
            status = SlopeStatus.FLAT

        return slope, slope_pct, status

    def _build_slope_rule(
        self, slope: float, slope_pct: float, status: SlopeStatus
    ) -> RuleResult:
        return RuleResult(
            name=self.RULE_EMA_SLOPE,
            passed=status is SlopeStatus.RISING,
            detail=(
                f"EMA{self.fast_period} slope over last {self.slope_lookback} "
                f"completed candles = {slope:+.5f} ({slope_pct:+.4%}) "
                f"-> Status = {status.value}"
            ),
        )

    # ------------------------------------------------------------------
    # Rule 3: EMA Separation
    # ------------------------------------------------------------------

    def _evaluate_separation(
        self, ema20: float, ema50: float
    ) -> tuple[float, float, bool]:
        separation = ema20 - ema50
        separation_pct = separation / ema50 if ema50 else 0.0
        passed = abs(separation_pct) >= self.min_ema_separation_pct
        return separation, separation_pct, passed

    def _build_separation_rule(
        self, separation: float, separation_pct: float, passed: bool
    ) -> RuleResult:
        return RuleResult(
            name=self.RULE_EMA_SEPARATION,
            passed=passed,
            detail=(
                f"|EMA{self.fast_period} - EMA{self.slow_period}| = "
                f"{abs(separation):.5f} ({abs(separation_pct):.4%} of EMA{self.slow_period}), "
                f"minimum required = {self.min_ema_separation_pct:.4%}"
            ),
        )

    # ------------------------------------------------------------------
    # Rule 1: EMA Alignment
    # ------------------------------------------------------------------

    def _build_alignment_rule(self, ema20: float, ema50: float) -> RuleResult:
        passed = ema20 > ema50
        return RuleResult(
            name=self.RULE_EMA_ALIGNMENT,
            passed=passed,
            detail=(
                f"EMA{self.fast_period} ({ema20:.5f}) "
                f"{'>' if passed else '<='} "
                f"EMA{self.slow_period} ({ema50:.5f})"
            ),
        )

    # ------------------------------------------------------------------
    # Rule 4: Market Structure (placeholder)
    # ------------------------------------------------------------------

    def evaluate_market_structure(self, history: list[Candle]) -> RuleResult:
        """
        Placeholder hook for a future Market Structure (HH/HL) rule.

        Not implemented yet. Always returns passed=None (NOT_IMPLEMENTED)
        and must never be used to gate bias or strength - see `_classify`,
        which does not reference this rule's outcome.
        """
        return RuleResult(
            name=self.RULE_MARKET_STRUCTURE,
            passed=None,
            detail="Market structure evaluation is not implemented yet.",
        )

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def _classify(
        self,
        alignment_passed: bool,
        slope_status: SlopeStatus,
        separation_ok: bool,
    ) -> tuple[MarketBias, TrendStrength]:
        if not alignment_passed or slope_status is SlopeStatus.FALLING:
            return MarketBias.NEUTRAL, TrendStrength.NONE

        if slope_status is SlopeStatus.RISING and separation_ok:
            return MarketBias.BULLISH, TrendStrength.STRONG

        return MarketBias.BULLISH, TrendStrength.WEAK

    # ------------------------------------------------------------------
    # Explainability
    # ------------------------------------------------------------------

    def _build_reason(
        self,
        strength: TrendStrength,
        alignment_rule: RuleResult,
        slope_status: SlopeStatus,
        separation_ok: bool,
    ) -> str:
        if not alignment_rule.passed:
            return (
                f"EMA{self.fast_period} is not above EMA{self.slow_period}, "
                "so there is no bullish trend to evaluate."
            )

        if slope_status is SlopeStatus.FALLING:
            return (
                f"EMA{self.fast_period} has started falling over the last "
                f"{self.slope_lookback} completed Daily candles."
            )

        lines = [
            "Healthy bullish trend."
            if strength is TrendStrength.STRONG
            else "Bullish trend, but quality is weak."
        ]
        lines.append(f"EMA{self.fast_period} remains above EMA{self.slow_period}.")
        lines.append(
            f"EMA{self.fast_period} continues rising."
            if slope_status is SlopeStatus.RISING
            else f"EMA{self.fast_period} is flat rather than clearly rising."
        )
        lines.append(
            "EMA separation remains sufficient."
            if separation_ok
            else "EMA separation has narrowed below the configured minimum."
        )
        return "\n".join(lines)

    def _build_explanation(
        self,
        candle: Candle,
        ema20: float,
        ema50: float,
        slope: float,
        separation: float,
        bias: MarketBias,
        strength: TrendStrength,
        rules: tuple[RuleResult, ...],
        slope_status: SlopeStatus,
        separation_ok: bool,
    ) -> str:
        alignment_rule, slope_rule, separation_rule, market_structure_rule = rules

        lines = [
            "================================",
            "Daily Trend Assessment",
            "",
            f"Date: {candle.timestamp.date()}",
            f"EMA{self.fast_period}: {ema20:.5f}",
            f"EMA{self.slow_period}: {ema50:.5f}",
            f"EMA Separation: {separation:+.5f}",
            f"EMA{self.fast_period} Slope: {slope:+.5f} ({slope_status.value})",
            "",
            f"Alignment: {_status_label(alignment_rule.passed)}",
            f"Slope: {_status_label(slope_rule.passed)}",
            f"Separation: {_status_label(separation_rule.passed)}",
            f"Market Structure: {_status_label(market_structure_rule.passed)}",
            "",
            f"Trend Strength: {strength.value}",
            "",
            "Reason:",
            "",
            self._build_reason(strength, alignment_rule, slope_status, separation_ok),
            "================================",
        ]
        return "\n".join(lines)

    def _insufficient_history_result(self, available: int) -> DailyTrendResult:
        required = max(self.min_history, self.slope_lookback)
        explanation = (
            "================================\n"
            "Daily Trend Assessment\n\n"
            "Insufficient daily history: "
            f"{available} candle(s) available, at least {required} required.\n"
            "================================"
        )
        rule = RuleResult(
            name=self.RULE_EMA_ALIGNMENT,
            passed=False,
            detail=explanation,
        )
        return DailyTrendResult(
            bias=MarketBias.NEUTRAL,
            strength=TrendStrength.NONE,
            rules=(rule,),
            ema20=None,
            ema50=None,
            ema20_slope=None,
            ema20_slope_status=None,
            ema_separation=None,
            ema_separation_pct=None,
            explanation=explanation,
        )


def _status_label(passed: bool | None) -> str:
    if passed is None:
        return "NOT_IMPLEMENTED"
    return "PASS" if passed else "FAIL"
