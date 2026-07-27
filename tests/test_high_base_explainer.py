import unittest
from datetime import datetime, timedelta

from core.market_context import MarketContext
from models.candle import Candle
from models.market_bias import MarketBias
from models.trend_assessment import DailyTrendResult, RuleResult, TrendStrength
from patterns.high_base_detector import HighBaseDetector
from validation.explainers import HighBaseExplainer, explainer_for
from validation.validation_report import ContextReview

# Same golden-path scenario as tests/test_high_base_detector.py, tuned to
# HighBaseDetector's default constants, so a review of the golden context
# reports every rule as PASS.
IMPULSE_CLOSES = [100.0, 100.5, 101.0, 101.5, 102.0]
BASE_HIGH = 102.9
BASE_LOW = 102.0
BASE_CLOSE = 102.4
BREAKOUT_CLOSE = 103.5

CHECK_ORDER = [
    "Daily Trend Assessment",
    "EMA Alignment",
    "EMA20 Rising",
    "Impulse Gain",
    "Base Width",
    "Breakout",
]
CHECK_COLUMNS = ["DailyTrend", "EMAAlignment", "EMASlope", "ImpulseGain", "BaseWidth", "Breakout"]


def _candle(index, open_, high, low, close) -> Candle:
    return Candle(
        symbol="USDJPY",
        timeframe="H1",
        timestamp=datetime(2024, 1, 1) + timedelta(hours=index),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=0.0,
    )


def _golden_candles(
    impulse_closes=IMPULSE_CLOSES,
    base_high=BASE_HIGH,
    base_low=BASE_LOW,
    breakout_close=BREAKOUT_CLOSE,
) -> tuple[Candle, ...]:
    candles = [_candle(i, c, c, c, c) for i, c in enumerate(impulse_closes)]
    base_start = len(candles)
    for i in range(10):
        candles.append(_candle(base_start + i, BASE_CLOSE, base_high, base_low, BASE_CLOSE))
    breakout_index = len(candles)
    candles.append(
        _candle(breakout_index, breakout_close, breakout_close + 0.1, breakout_close - 0.5, breakout_close)
    )
    return tuple(candles)


def _daily_assessment(strength=TrendStrength.STRONG, bias=MarketBias.BULLISH) -> DailyTrendResult:
    # rules/explanation mirror the shape DailyTrendAssessment.assess()
    # actually produces (see strategies/daily_trend_assessment.py), so
    # HighBaseExplainer's _daily_trend_details() - which reads both -
    # has real sub-rule data to unpack, the same as it would at runtime.
    return DailyTrendResult(
        bias=bias,
        strength=strength,
        rules=(
            RuleResult(
                name="ema_alignment",
                passed=True,
                detail="EMA20 (154.23000) > EMA50 (153.10000)",
            ),
            RuleResult(
                name="ema20_slope",
                passed=True,
                detail=(
                    "EMA20 slope over last 5 completed candles = +0.05000 "
                    "(+0.0324%) -> Status = Rising"
                ),
            ),
            RuleResult(
                name="ema_separation",
                passed=True,
                detail="|EMA20 - EMA50| = 1.13000 (0.7381% of EMA50), minimum required = 0.0000%",
            ),
        ),
        ema20=154.23,
        ema50=153.10,
        ema20_slope=0.05,
        ema20_slope_status=None,
        ema_separation=1.13,
        ema_separation_pct=0.0074,
        explanation=(
            "================================\n"
            "Daily Trend Assessment\n\n"
            "Date: 2024-01-01\n"
            "EMA20: 154.23000\n"
            "EMA50: 153.10000\n\n"
            "Trend Strength: STRONG\n\n"
            "Reason:\n\n"
            "Healthy bullish trend.\n"
            "================================"
        ),
    )


def _golden_context(**overrides) -> MarketContext:
    candles = overrides.pop("candles", None) or _golden_candles()
    defaults = dict(
        symbol="USDJPY",
        timeframe="H1",
        timestamp=candles[-1].timestamp,
        candles=candles,
        ema20=102.5,
        ema50=101.0,
        ema20_history=(101.0, 101.5, 102.0, 102.3, 102.5),
        daily_assessment=_daily_assessment(),
    )
    defaults.update(overrides)
    return MarketContext(**defaults)


class HighBaseExplainerGoldenPathTests(unittest.TestCase):
    def setUp(self):
        self.explainer = HighBaseExplainer()

    def test_golden_path_all_checks_pass_and_signal_detected(self):
        review = self.explainer.explain(_golden_context())

        self.assertIsInstance(review, ContextReview)
        self.assertTrue(review.signal_detected)
        self.assertEqual(review.failure_reason, "")
        self.assertTrue(all(check.passed for check in review.checks))

    def test_review_carries_context_identity_fields(self):
        context = _golden_context()

        review = self.explainer.explain(context)

        self.assertEqual(review.timestamp, context.timestamp)
        self.assertEqual(review.symbol, context.symbol)
        self.assertEqual(review.timeframe, context.timeframe)
        self.assertEqual(review.detector, HighBaseDetector.NAME)
        self.assertEqual(review.pattern_label, "High Base")

    def test_check_names_and_columns_are_stable_and_ordered(self):
        review = self.explainer.explain(_golden_context())

        self.assertEqual([c.name for c in review.checks], CHECK_ORDER)
        self.assertEqual([c.column for c in review.checks], CHECK_COLUMNS)

    def test_deterministic_output(self):
        context = _golden_context()

        first = self.explainer.explain(context)
        second = self.explainer.explain(context)

        self.assertEqual(first, second)


class HighBaseExplainerRuleFailureTests(unittest.TestCase):
    def setUp(self):
        self.explainer = HighBaseExplainer()

    def _check(self, review: ContextReview, name: str):
        return next(c for c in review.checks if c.name == name)

    def test_daily_trend_failure_is_reported_with_actual_strength(self):
        context = _golden_context(daily_assessment=_daily_assessment(strength=TrendStrength.WEAK))

        review = self.explainer.explain(context)

        check = self._check(review, "Daily Trend Assessment")
        self.assertFalse(check.passed)
        self.assertEqual(check.expected, "STRONG")
        self.assertEqual(check.actual, "WEAK")
        self.assertFalse(review.signal_detected)
        self.assertEqual(review.failure_reason, "Daily trend is not strong.")

    def test_missing_daily_assessment_reports_na_actual(self):
        context = _golden_context(daily_assessment=None)

        review = self.explainer.explain(context)

        check = self._check(review, "Daily Trend Assessment")
        self.assertFalse(check.passed)
        self.assertIn("N/A", check.actual)

    def test_ema_alignment_failure_reports_both_values(self):
        context = _golden_context(ema20=100.0, ema50=101.0)

        review = self.explainer.explain(context)

        check = self._check(review, "EMA Alignment")
        self.assertFalse(check.passed)
        self.assertIn("EMA20=100.00000", check.actual)
        self.assertIn("EMA50=101.00000", check.actual)
        self.assertEqual(review.failure_reason, "EMA20 is not above EMA50.")

    def test_ema_slope_failure_when_falling(self):
        context = _golden_context(ema20_history=(102.5, 102.5, 102.0, 101.5, 101.0))

        review = self.explainer.explain(context)

        check = self._check(review, "EMA20 Rising")
        self.assertFalse(check.passed)
        self.assertEqual(check.actual, "Flat or falling")

    def test_ema_slope_insufficient_history_is_reported_distinctly(self):
        context = _golden_context(ema20_history=(102.5,))

        review = self.explainer.explain(context)

        check = self._check(review, "EMA20 Rising")
        self.assertFalse(check.passed)
        self.assertIn("N/A", check.actual)

    def test_impulse_gain_reports_actual_percentage(self):
        flat_impulse = [100.0, 100.0, 100.0, 100.0, 100.0]
        context = _golden_context(candles=_golden_candles(impulse_closes=flat_impulse))

        review = self.explainer.explain(context)

        check = self._check(review, "Impulse Gain")
        self.assertFalse(check.passed)
        self.assertEqual(check.actual, "0.00%")
        self.assertEqual(check.expected, ">= 1.00%")
        self.assertEqual(review.failure_reason, "Impulse too weak.")

    def test_impulse_gain_not_evaluated_when_history_insufficient(self):
        context = _golden_context(candles=_golden_candles()[-3:])

        review = self.explainer.explain(context)

        check = self._check(review, "Impulse Gain")
        self.assertIsNone(check.passed)
        self.assertIn("N/A", check.actual)

    def test_base_width_reports_actual_percentage(self):
        context = _golden_context(candles=_golden_candles(base_high=110.0))

        review = self.explainer.explain(context)

        check = self._check(review, "Base Width")
        self.assertFalse(check.passed)
        self.assertEqual(review.failure_reason, "Base range too wide.")

    def test_breakout_reports_close_and_base_high(self):
        context = _golden_context(candles=_golden_candles(breakout_close=102.5))

        review = self.explainer.explain(context)

        check = self._check(review, "Breakout")
        self.assertFalse(check.passed)
        self.assertIn("Close = 102.50000", check.actual)
        self.assertEqual(review.failure_reason, "No confirmed breakout above the base high.")

    def test_failure_reason_reports_earliest_failed_rule_in_canonical_order(self):
        # Both EMA Alignment (rule 2) and Impulse Gain (rule 4) fail;
        # the earlier rule in canonical order should be reported.
        context = _golden_context(
            ema20=100.0,
            ema50=101.0,
            candles=_golden_candles(impulse_closes=[100.0] * 5),
        )

        review = self.explainer.explain(context)

        self.assertEqual(review.failure_reason, "EMA20 is not above EMA50.")

    def test_multiple_rules_can_be_evaluated_after_an_earlier_failure(self):
        # Even though Daily Trend fails first, later rules are still
        # independently evaluated (unlike HighBaseDetector.detect(),
        # which would short-circuit here) - the whole point of review
        # mode is to see the full picture.
        context = _golden_context(daily_assessment=_daily_assessment(strength=TrendStrength.WEAK))

        review = self.explainer.explain(context)

        breakout_check = self._check(review, "Breakout")
        self.assertTrue(breakout_check.passed)


class ExplainerRegistryTests(unittest.TestCase):
    def test_explainer_for_returns_high_base_explainer(self):
        explainer = explainer_for(HighBaseDetector())

        self.assertIsInstance(explainer, HighBaseExplainer)

    def test_explainer_for_raises_for_unregistered_detector(self):
        class UnregisteredDetector:
            NAME = "NotRealDetector"

            def detect(self, context):
                return None

        with self.assertRaises(ValueError):
            explainer_for(UnregisteredDetector())


class HighBaseExplainerTraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.explainer = HighBaseExplainer()

    def test_traceability_identifies_daily_and_h1_candles(self):
        context = _golden_context()

        review = self.explainer.explain(context)

        labels = [item.label for item in review.traceability]
        self.assertEqual(labels, ["Daily Candle", "H1 Candle"])

        h1_item = next(item for item in review.traceability if item.label == "H1 Candle")
        self.assertEqual(h1_item.value, context.timestamp.strftime("%Y-%m-%d %H:%M"))

    def test_daily_candle_traceability_reports_na_without_assessment(self):
        context = _golden_context(daily_assessment=None)

        review = self.explainer.explain(context)

        daily_item = next(item for item in review.traceability if item.label == "Daily Candle")
        self.assertIn("N/A", daily_item.value)

    def test_traceability_is_deterministic(self):
        context = _golden_context()

        first = self.explainer.explain(context).traceability
        second = self.explainer.explain(context).traceability

        self.assertEqual(first, second)


class HighBaseExplainerDailyTrendDetailsTests(unittest.TestCase):
    def setUp(self):
        self.explainer = HighBaseExplainer()

    def _daily_trend_check(self, context):
        review = self.explainer.explain(context)
        return next(c for c in review.checks if c.name == "Daily Trend Assessment")

    def test_golden_path_details_cover_every_sub_rule(self):
        check = self._daily_trend_check(_golden_context())

        labels = [item.label for item in check.details]
        self.assertEqual(
            labels,
            [
                "Daily Candle Used",
                "Bias",
                "Strength",
                "EMA20",
                "EMA50",
                "Alignment Rule",
                "EMA20 Slope",
                "EMA Separation",
                "Final Classification",
            ],
        )

    def test_golden_path_sub_rules_all_pass_and_no_reason(self):
        check = self._daily_trend_check(_golden_context())

        sub_rules = {item.label: item for item in check.details}
        self.assertTrue(sub_rules["Alignment Rule"].status)
        self.assertTrue(sub_rules["EMA20 Slope"].status)
        self.assertTrue(sub_rules["EMA Separation"].status)
        self.assertEqual(sub_rules["Final Classification"].value, "BULLISH STRONG")
        self.assertNotIn("Reason", sub_rules)

    def test_neutral_assessment_reports_bias_only_classification_and_reason(self):
        neutral_assessment = DailyTrendResult(
            bias=MarketBias.NEUTRAL,
            strength=TrendStrength.NONE,
            rules=(),
            ema20=100.0,
            ema50=101.0,
            ema20_slope=None,
            ema20_slope_status=None,
            ema_separation=None,
            ema_separation_pct=None,
            explanation=(
                "================================\n"
                "Daily Trend Assessment\n\n"
                "Date: 2026-04-17\n"
                "EMA20: 100.00000\n"
                "EMA50: 101.00000\n\n"
                "Trend Strength: NONE\n\n"
                "Reason:\n\n"
                "EMA20 is not above EMA50, so there is no bullish trend to evaluate.\n"
                "================================"
            ),
        )
        context = _golden_context(daily_assessment=neutral_assessment)

        check = self._daily_trend_check(context)

        sub_rules = {item.label: item for item in check.details}
        self.assertEqual(sub_rules["Final Classification"].value, "NEUTRAL")
        self.assertIn("EMA20 is not above EMA50", sub_rules["Reason"].value)

    def test_missing_assessment_reports_single_na_detail(self):
        check = self._daily_trend_check(_golden_context(daily_assessment=None))

        self.assertEqual(len(check.details), 1)
        self.assertIn("N/A", check.details[0].value)

    def test_details_do_not_affect_expected_actual_used_by_review_mode(self):
        # Review mode (format_console_review) still reads expected/actual
        # directly - details must be additive, not a replacement.
        check = self._daily_trend_check(_golden_context())

        self.assertEqual(check.expected, "STRONG")
        self.assertEqual(check.actual, "STRONG")


class HighBaseExplainerFormulaAndLabelTests(unittest.TestCase):
    def setUp(self):
        self.explainer = HighBaseExplainer()

    def _check(self, context, name):
        review = self.explainer.explain(context)
        return next(c for c in review.checks if c.name == name)

    def test_impulse_gain_has_formula(self):
        check = self._check(_golden_context(), "Impulse Gain")

        self.assertEqual(check.formula, "(end_close - start_close) / start_close")

    def test_base_width_has_formula(self):
        check = self._check(_golden_context(), "Base Width")

        self.assertEqual(check.formula, "(base_high - base_low) / base_low")

    def test_breakout_uses_required_label(self):
        check = self._check(_golden_context(), "Breakout")

        self.assertEqual(check.expected_label, "Required")

    def test_breakout_threshold_accounts_for_buffer_pct(self):
        # Regression test: the explainer's displayed "Required" close
        # must match HighBaseDetector._passes_hb006_breakout's own
        # required_close = base_high * (1 + breakout_buffer_pct), not
        # the bare base_high, once a nonzero buffer is configured.
        buffered_detector = HighBaseDetector(breakout_buffer_pct=0.01)
        explainer = HighBaseExplainer(buffered_detector)
        context = _golden_context()

        review = explainer.explain(context)
        breakout_check = next(c for c in review.checks if c.name == "Breakout")

        base_high = BASE_HIGH
        expected_required_close = base_high * 1.01
        self.assertIn(f"{expected_required_close:.5f}", breakout_check.expected)

        # And the PASS/FAIL decision itself must match the detector's
        # own evaluation with that same buffer.
        self.assertEqual(
            breakout_check.passed,
            buffered_detector._passes_hb006_breakout(context.latest_candle, base_high),
        )


if __name__ == "__main__":
    unittest.main()
