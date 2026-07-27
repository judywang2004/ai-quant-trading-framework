"""
Detector-specific adapters that turn a MarketContext + PatternDetector
pairing into a generic ContextReview (validation/validation_report.py).

This is the one place per-detector business knowledge belongs: rule
names, "expected"/"actual" business descriptions, and failure reasons.
validation_formatter.py and demo_signal_engine.py never need to know
about HighBase-specific rule IDs (HB-001..HB-007) or any future
detector's internals - they only ever consume the generic
RuleCheck/ContextReview shape an explainer produces.

Explainers deliberately read a detector's already-existing rule methods
(e.g. HighBaseDetector._passes_hb00N_...) rather than re-implementing
detection logic. Duplicating those thresholds/formulas here would risk
a review silently drifting from what the detector actually does; this
task must not change detector behavior, only explain it, so evaluating
each rule via the detector's own methods - without the short-circuiting
`detect()` does - is what lets every rule be shown even after an
earlier one has failed.

A future detector plugs into the same review/export pipeline by
implementing DetectorExplainer and calling register_explainer() - no
change to demo_signal_engine.py, validation_formatter.py, or
validation_report.py is required.
"""

from typing import Protocol, runtime_checkable

from core.market_context import MarketContext
from models.trend_assessment import DailyTrendResult, TrendStrength
from patterns.high_base_detector import HighBaseDetector

from validation.validation_report import ContextReview, DetailItem, RuleCheck

INSUFFICIENT_HISTORY = "N/A (insufficient history)"

# Matches validation_formatter.TIMESTAMP_FORMAT - kept as its own local
# constant rather than imported, since it's a trivial formatting detail
# and explainers.py otherwise has no dependency on validation_formatter.
_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M"


@runtime_checkable
class DetectorExplainer(Protocol):
    def explain(self, context: MarketContext) -> ContextReview:
        """Evaluate every rule of the wrapped detector against `context`
        and return a full ContextReview, whether or not a signal was
        ultimately detected."""
        ...


class HighBaseExplainer:
    """Explains a HighBaseDetector's rule-by-rule evaluation of one
    MarketContext, independent of whether it produced an Opportunity."""

    PATTERN_LABEL = "High Base"

    _FAILURE_MESSAGES = {
        "Daily Trend Assessment": "Daily trend is not strong.",
        "EMA Alignment": "EMA20 is not above EMA50.",
        "EMA20 Rising": "EMA20 is flat or falling.",
        "Impulse Gain": "Impulse too weak.",
        "Base Width": "Base range too wide.",
        "Breakout": "No confirmed breakout above the base high.",
    }

    def __init__(self, detector: HighBaseDetector | None = None):
        self.detector = detector or HighBaseDetector()

    def explain(self, context: MarketContext) -> ContextReview:
        detector = self.detector
        base_candles = detector._base_candles(context)

        checks = (
            self._daily_trend_check(context),
            self._ema_alignment_check(context),
            self._ema_slope_check(context),
            self._impulse_gain_check(context, base_candles),
            self._base_width_check(base_candles),
            self._breakout_check(context, base_candles),
        )

        signal_detected = all(check.passed for check in checks)
        failure_reason = "" if signal_detected else self._failure_reason(checks)

        return ContextReview(
            timestamp=context.timestamp,
            symbol=context.symbol,
            timeframe=context.timeframe,
            detector=getattr(detector, "NAME", type(detector).__name__),
            pattern_label=self.PATTERN_LABEL,
            checks=checks,
            signal_detected=signal_detected,
            failure_reason=failure_reason,
            traceability=self._traceability(context),
        )

    # ------------------------------------------------------------------
    # Traceability: every raw candle this decision was based on
    # ------------------------------------------------------------------

    def _traceability(self, context: MarketContext) -> tuple[DetailItem, ...]:
        return (
            DetailItem("Daily Candle", _daily_candle_used(context.daily_assessment)),
            DetailItem("H1 Candle", context.timestamp.strftime(_TIMESTAMP_FORMAT)),
        )

    # ------------------------------------------------------------------
    # Individual rule explanations (mirrors HighBaseDetector.detect())
    # ------------------------------------------------------------------

    def _daily_trend_check(self, context: MarketContext) -> RuleCheck:
        assessment = context.daily_assessment
        actual = assessment.strength.value if assessment is not None else "N/A (no daily assessment)"

        return RuleCheck(
            name="Daily Trend Assessment",
            column="DailyTrend",
            expected=TrendStrength.STRONG.value,
            actual=actual,
            passed=self.detector._passes_hb001_daily_trend_strong(context),
            details=self._daily_trend_details(assessment),
        )

    def _daily_trend_details(self, assessment: DailyTrendResult | None) -> tuple[DetailItem, ...]:
        """
        Unpacks context.daily_assessment (DailyTrendResult) into
        research-mode detail lines: the sub-rules DailyTrendAssessment
        itself already evaluated (alignment/slope/separation), each
        with its own real PASS/FAIL, plus the final classification.

        Reuses each RuleResult's own `.detail` text verbatim rather than
        recomputing slope/separation thresholds here - those thresholds
        belong to DailyTrendAssessment's configuration, which this
        explainer has no access to (and must not duplicate/guess at) -
        so this only ever reads values DailyTrendAssessment already
        computed and exposed via DailyTrendResult, never HighBase logic.
        """
        if assessment is None:
            return (DetailItem("Daily Trend Assessment", "N/A (no daily assessment)"),)

        items = [
            DetailItem("Daily Candle Used", _daily_candle_used(assessment)),
            DetailItem("Bias", assessment.bias.name),
            DetailItem("Strength", assessment.strength.value),
        ]

        if assessment.ema20 is not None:
            items.append(DetailItem("EMA20", f"{assessment.ema20:.5f}"))
        if assessment.ema50 is not None:
            items.append(DetailItem("EMA50", f"{assessment.ema50:.5f}"))

        alignment_rule = assessment.rule("ema_alignment")
        if alignment_rule is not None:
            items.append(DetailItem("Alignment Rule", alignment_rule.detail, status=alignment_rule.passed))

        slope_rule = assessment.rule("ema20_slope")
        if slope_rule is not None:
            items.append(DetailItem("EMA20 Slope", slope_rule.detail, status=slope_rule.passed))

        separation_rule = assessment.rule("ema_separation")
        if separation_rule is not None:
            items.append(DetailItem("EMA Separation", separation_rule.detail, status=separation_rule.passed))

        if assessment.strength is TrendStrength.NONE:
            # NONE means "no trend at all" - pairing it with the bias
            # ("NEUTRAL NONE") would be redundant, so just the bias.
            items.append(DetailItem("Final Classification", assessment.bias.name))
            items.append(DetailItem("Reason", _daily_neutral_reason(assessment)))
        else:
            items.append(
                DetailItem("Final Classification", f"{assessment.bias.name} {assessment.strength.value}")
            )

        return tuple(items)

    def _ema_alignment_check(self, context: MarketContext) -> RuleCheck:
        if context.ema20 is not None and context.ema50 is not None:
            actual = f"EMA20={context.ema20:.5f}, EMA50={context.ema50:.5f}"
        else:
            actual = "N/A (missing EMA values)"

        return RuleCheck(
            name="EMA Alignment",
            column="EMAAlignment",
            expected="EMA20 > EMA50",
            actual=actual,
            passed=self.detector._passes_hb002_ema_alignment(context),
        )

    def _ema_slope_check(self, context: MarketContext) -> RuleCheck:
        passed = self.detector._passes_hb003_ema20_rising(context)

        if len(context.ema20_history) < 2:
            actual = "N/A (fewer than 2 EMA20 history points)"
        else:
            actual = "Rising" if passed else "Flat or falling"

        return RuleCheck(
            name="EMA20 Rising",
            column="EMASlope",
            expected="Rising",
            actual=actual,
            passed=passed,
        )

    def _impulse_gain_check(self, context: MarketContext, base_candles) -> RuleCheck:
        detector = self.detector
        expected = f">= {detector.impulse_min_gain_pct * 100:.2f}%"

        impulse_candles = (
            detector._impulse_candles(context, base_candles) if base_candles is not None else None
        )
        if not impulse_candles:
            return RuleCheck(
                name="Impulse Gain",
                column="ImpulseGain",
                expected=expected,
                actual=INSUFFICIENT_HISTORY,
                passed=None,
            )

        start_close = impulse_candles[0].close
        end_close = impulse_candles[-1].close
        gain_pct = (end_close - start_close) / start_close if start_close else 0.0

        return RuleCheck(
            name="Impulse Gain",
            column="ImpulseGain",
            expected=expected,
            actual=f"{gain_pct * 100:.2f}%",
            formula="(end_close - start_close) / start_close",
            passed=detector._passes_hb004_impulse_leg(context, base_candles),
        )

    def _base_width_check(self, base_candles) -> RuleCheck:
        detector = self.detector
        expected = f"<= {detector.max_base_range_pct * 100:.2f}%"

        if base_candles is None:
            return RuleCheck(
                name="Base Width",
                column="BaseWidth",
                expected=expected,
                actual=INSUFFICIENT_HISTORY,
                passed=None,
            )

        base_high, base_low = detector._base_range(base_candles)
        if base_low <= 0:
            return RuleCheck(
                name="Base Width",
                column="BaseWidth",
                expected=expected,
                actual=INSUFFICIENT_HISTORY,
                passed=None,
            )

        range_pct = (base_high - base_low) / base_low
        return RuleCheck(
            name="Base Width",
            column="BaseWidth",
            expected=expected,
            actual=f"{range_pct * 100:.2f}%",
            formula="(base_high - base_low) / base_low",
            passed=detector._passes_hb005_high_base(base_high, base_low),
        )

    def _breakout_check(self, context: MarketContext, base_candles) -> RuleCheck:
        detector = self.detector
        breakout_candle = context.latest_candle

        if base_candles is None or breakout_candle is None:
            return RuleCheck(
                name="Breakout",
                column="Breakout",
                expected="Close > base high",
                actual=INSUFFICIENT_HISTORY,
                passed=None,
            )

        base_high, _ = detector._base_range(base_candles)
        # Mirrors HighBaseDetector._passes_hb006_breakout's own
        # required_close calculation exactly, so the displayed
        # threshold stays correct even when breakout_buffer_pct != 0.
        required_close = base_high * (1 + detector.breakout_buffer_pct)

        return RuleCheck(
            name="Breakout",
            column="Breakout",
            expected=f"Close > {required_close:.5f}",
            expected_label="Required",
            actual=f"Close = {breakout_candle.close:.5f}",
            formula="required_close = base_high * (1 + breakout_buffer_pct)",
            passed=detector._passes_hb006_breakout(breakout_candle, base_high),
        )

    def _failure_reason(self, checks: tuple[RuleCheck, ...]) -> str:
        failed = next((check for check in checks if check.passed is False), None)
        if failed is not None:
            return self._FAILURE_MESSAGES.get(failed.name, f"{failed.name} failed.")

        unevaluated = next((check for check in checks if check.passed is None), None)
        if unevaluated is not None:
            return f"{unevaluated.name}: insufficient history to evaluate."

        return ""


# ----------------------------------------------------------------------
# DailyTrendResult introspection helpers
#
# DailyTrendResult does not expose the daily candle's date, or a
# structured "why NEUTRAL" reason, as fields of their own - only baked
# into its human-readable `explanation` text (built by
# DailyTrendAssessment._build_explanation / _build_reason). Parsing that
# text here - rather than recomputing the date or the reason from
# scratch - keeps this explainer in lockstep with DailyTrendAssessment's
# own explainability output without duplicating its logic (the same
# principle as calling HighBaseDetector's own _passes_hb00N_ methods
# above, applied to the daily side).
# ----------------------------------------------------------------------


def _daily_candle_used(assessment: DailyTrendResult | None) -> str:
    if assessment is None:
        return "N/A (no daily assessment)"

    for line in assessment.explanation.splitlines():
        if line.startswith("Date: "):
            return line.removeprefix("Date: ").strip()

    return "N/A (insufficient daily history)"


def _daily_neutral_reason(assessment: DailyTrendResult) -> str:
    lines = assessment.explanation.splitlines()
    try:
        reason_start = lines.index("Reason:") + 1
    except ValueError:
        return "Not available."

    reason_lines = []
    for line in lines[reason_start:]:
        stripped = line.strip()
        if not stripped:
            if reason_lines:
                break
            continue
        if stripped.startswith("="):
            break
        reason_lines.append(stripped)

    return " ".join(reason_lines) if reason_lines else "Not available."


_EXPLAINERS: dict[str, type] = {}


def register_explainer(detector_name: str, explainer_cls: type) -> None:
    """Register an explainer class for a detector, keyed by its NAME.

    Lets a future detector plug into the same review/export pipeline
    (demo_signal_engine.py, validation_formatter.py) by registering its
    own explainer here, without either of those modules changing.
    """
    _EXPLAINERS[detector_name] = explainer_cls


def explainer_for(detector) -> DetectorExplainer:
    """Look up the registered explainer for `detector` and construct it.

    Raises ValueError if no explainer has been registered for this
    detector - explicit and early, rather than silently producing an
    empty or misleading review.
    """
    name = getattr(detector, "NAME", type(detector).__name__)
    explainer_cls = _EXPLAINERS.get(name)
    if explainer_cls is None:
        raise ValueError(f"No explainer registered for detector '{name}'.")

    return explainer_cls(detector)


register_explainer(HighBaseDetector.NAME, HighBaseExplainer)
