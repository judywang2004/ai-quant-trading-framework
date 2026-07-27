import csv
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from validation.validation_formatter import (
    format_dataset_summary,
    format_research_review,
    format_research_summary,
    write_csv_export,
)
from validation.validation_report import (
    ContextReview,
    DatasetSummary,
    DetailItem,
    ResearchSummary,
    RuleCheck,
    RuleFailureCount,
    build_research_summary,
)

# Deliberately NOT High Base specific: proves the research report layer
# (data model, aggregation, and formatting) is generic and would work
# unchanged for a future detector's own explainer.
FAKE_PATTERN = "Test Pattern"
FAKE_DETECTOR = "FakeDetector"


def _check(name, column, passed, **kwargs) -> RuleCheck:
    return RuleCheck(name=name, column=column, passed=passed, **kwargs)


def _review(
    signal_detected=True,
    failure_reason="",
    checks=None,
    traceability=None,
    timestamp=datetime(2025, 3, 12, 8, 0),
) -> ContextReview:
    return ContextReview(
        timestamp=timestamp,
        symbol="USDJPY",
        timeframe="H1",
        detector=FAKE_DETECTOR,
        pattern_label=FAKE_PATTERN,
        checks=tuple(checks) if checks is not None else (
            _check("Rule One", "RuleOne", True),
            _check("Rule Two", "RuleTwo", False),
        ),
        signal_detected=signal_detected,
        failure_reason=failure_reason,
        traceability=tuple(traceability) if traceability is not None else (),
    )


class RuleCheckDetailsTests(unittest.TestCase):
    def test_details_default_to_empty_tuple(self):
        check = _check("Rule", "Rule", True)

        self.assertEqual(check.details, ())

    def test_details_list_is_coerced_to_tuple(self):
        check = _check("Rule", "Rule", True, details=[DetailItem("A", "1")])

        self.assertIsInstance(check.details, tuple)

    def test_expected_label_defaults_to_threshold(self):
        check = _check("Rule", "Rule", True)

        self.assertEqual(check.expected_label, "Threshold")

    def test_formula_and_expected_label_are_overridable(self):
        check = _check(
            "Breakout", "Breakout", False, formula="x > y", expected_label="Required"
        )

        self.assertEqual(check.formula, "x > y")
        self.assertEqual(check.expected_label, "Required")


class ContextReviewTraceabilityTests(unittest.TestCase):
    def test_traceability_defaults_to_empty_tuple(self):
        review = _review()

        self.assertEqual(review.traceability, ())

    def test_traceability_list_is_coerced_to_tuple(self):
        review = _review(traceability=[DetailItem("Daily Candle", "2026-03-16")])

        self.assertIsInstance(review.traceability, tuple)
        self.assertEqual(review.traceability[0].label, "Daily Candle")


class FormatResearchReviewTests(unittest.TestCase):
    def test_contains_identity_and_tradingview_sections(self):
        text = format_research_review(_review(), index=3, total=20)

        self.assertIn("Research Review 3 / 20", text)
        self.assertIn("Symbol:", text)
        self.assertIn("USDJPY", text)
        self.assertIn("TradingView", text)
        self.assertIn("Ticker:", text)
        self.assertIn("Go to candle:", text)

    def test_traceability_section_lists_every_item(self):
        review = _review(
            traceability=[
                DetailItem("Daily Candle", "2026-03-16"),
                DetailItem("H1 Candle", "2026-03-17 04:00"),
            ]
        )

        text = format_research_review(review, index=1, total=1)

        self.assertIn("Traceability", text)
        self.assertIn("Daily Candle", text)
        self.assertIn("2026-03-16", text)
        self.assertIn("H1 Candle", text)
        self.assertIn("2026-03-17 04:00", text)

    def test_traceability_section_omitted_when_empty(self):
        text = format_research_review(_review(traceability=[]), index=1, total=1)

        self.assertNotIn("Traceability", text)

    def test_check_without_details_prints_decision_formula_threshold_actual(self):
        checks = [
            _check(
                "Impulse Gain",
                "ImpulseGain",
                False,
                formula="(end_close - start_close) / start_close",
                expected=">= 1.00%",
                actual="0.11%",
            )
        ]
        text = format_research_review(_review(checks=checks), index=1, total=1)

        self.assertIn("Impulse Gain", text)
        self.assertIn("Decision", text)
        self.assertIn("FAIL", text)
        self.assertIn("Formula", text)
        self.assertIn("(end_close - start_close) / start_close", text)
        self.assertIn("Threshold", text)
        self.assertIn(">= 1.00%", text)
        self.assertIn("Actual", text)
        self.assertIn("0.11%", text)

    def test_expected_label_override_renders_instead_of_threshold(self):
        checks = [
            _check(
                "Breakout",
                "Breakout",
                False,
                expected="Close > 159.45300",
                expected_label="Required",
                actual="Close = 159.36700",
            )
        ]
        text = format_research_review(_review(checks=checks), index=1, total=1)

        self.assertIn("Required", text)
        self.assertIn("Close > 159.45300", text)

    def test_check_with_details_prints_details_and_suppresses_flat_fields(self):
        # A composite check (e.g. Daily Trend Assessment) tells its story
        # through `details` - printing a separate Threshold/Actual after
        # would just repeat the same conclusion.
        checks = [
            _check(
                "Composite Rule",
                "Composite",
                True,
                expected="SHOULD NOT APPEAR",
                actual="SHOULD NOT APPEAR",
                formula="SHOULD NOT APPEAR",
                details=[
                    DetailItem("Sub Rule A", "value a", status=True),
                    DetailItem("Sub Rule B", "value b", status=False),
                    DetailItem("Final Classification", "X Y"),
                ],
            )
        ]
        text = format_research_review(_review(checks=checks), index=1, total=1)

        self.assertIn("Sub Rule A", text)
        self.assertIn("value a", text)
        self.assertIn("Sub Rule B", text)
        self.assertIn("Final Classification", text)
        self.assertIn("X Y", text)
        self.assertNotIn("SHOULD NOT APPEAR", text)

    def test_detail_item_status_renders_inline_pass_fail(self):
        checks = [
            _check(
                "Composite Rule",
                "Composite",
                True,
                details=[DetailItem("Sub Rule", "value", status=False)],
            )
        ]
        text = format_research_review(_review(checks=checks), index=1, total=1)

        # The sub-rule's own FAIL should appear even though the parent
        # check's overall Decision is PASS.
        lines = text.splitlines()
        sub_rule_index = lines.index("Sub Rule")
        self.assertIn("FAIL", lines[sub_rule_index : sub_rule_index + 4])

    def test_final_result_and_reason(self):
        text = format_research_review(
            _review(signal_detected=False, failure_reason="Impulse too weak."), index=1, total=1
        )

        self.assertIn("FINAL RESULT", text)
        self.assertIn("NO SIGNAL", text)
        self.assertIn("Reason", text)
        self.assertIn("Impulse too weak.", text)

    def test_signal_detected_omits_reason(self):
        text = format_research_review(
            _review(signal_detected=True, failure_reason=""), index=1, total=1
        )

        self.assertIn("SIGNAL DETECTED", text)
        self.assertNotIn("Reason", text)

    def test_does_not_include_manual_review_checklist(self):
        # That checklist is review-mode only (format_console_review).
        text = format_research_review(_review(), index=1, total=1)

        self.assertNotIn("Manual TradingView Review", text)

    def test_output_is_deterministic(self):
        review = _review()

        first = format_research_review(review, index=1, total=1)
        second = format_research_review(review, index=1, total=1)

        self.assertEqual(first, second)


class FormatDatasetSummaryTests(unittest.TestCase):
    def test_reports_first_last_available_and_selected(self):
        summary = DatasetSummary(
            first_context_timestamp=datetime(2026, 3, 17, 1, 0),
            last_context_timestamp=datetime(2026, 7, 10, 22, 0),
            contexts_available=1998,
            requested_start=date(2026, 3, 1),
            requested_end=date(2026, 3, 15),
            contexts_selected=20,
        )

        text = format_dataset_summary(summary)

        self.assertIn("Dataset", text)
        self.assertIn("First Context", text)
        self.assertIn("2026-03-17 01:00", text)
        self.assertIn("Last Context", text)
        self.assertIn("2026-07-10 22:00", text)
        self.assertIn("Contexts Available", text)
        self.assertIn("1998", text)
        self.assertIn("Requested Range", text)
        self.assertIn("2026-03-01", text)
        self.assertIn("2026-03-15", text)
        self.assertIn("Contexts Selected", text)
        self.assertIn("20", text)

    def test_unbounded_range_when_no_dates_requested(self):
        summary = DatasetSummary(
            first_context_timestamp=datetime(2026, 3, 17, 1, 0),
            last_context_timestamp=datetime(2026, 7, 10, 22, 0),
            contexts_available=1998,
            requested_start=None,
            requested_end=None,
            contexts_selected=1998,
        )

        text = format_dataset_summary(summary)

        self.assertIn("(unbounded)", text)

    def test_empty_dataset_reports_na(self):
        summary = DatasetSummary(
            first_context_timestamp=None,
            last_context_timestamp=None,
            contexts_available=0,
            requested_start=None,
            requested_end=None,
            contexts_selected=0,
        )

        text = format_dataset_summary(summary)

        self.assertIn("N/A", text)
        self.assertIn("0", text)


class BuildResearchSummaryTests(unittest.TestCase):
    def test_empty_reviews_produce_zeroed_summary(self):
        summary = build_research_summary([])

        self.assertEqual(summary.contexts_reviewed, 0)
        self.assertEqual(summary.signals_detected, 0)
        self.assertEqual(summary.rule_failure_counts, ())
        self.assertIsNone(summary.most_common_failure)

    def test_counts_contexts_and_signals(self):
        reviews = [
            _review(signal_detected=True),
            _review(signal_detected=False),
            _review(signal_detected=False),
        ]

        summary = build_research_summary(reviews)

        self.assertEqual(summary.contexts_reviewed, 3)
        self.assertEqual(summary.signals_detected, 1)

    def test_counts_failures_per_rule_name(self):
        reviews = [
            _review(checks=[_check("Rule A", "A", True), _check("Rule B", "B", False)]),
            _review(checks=[_check("Rule A", "A", False), _check("Rule B", "B", False)]),
            _review(checks=[_check("Rule A", "A", True), _check("Rule B", "B", True)]),
        ]

        summary = build_research_summary(reviews)

        counts = {r.name: r.failures for r in summary.rule_failure_counts}
        self.assertEqual(counts["Rule A"], 1)
        self.assertEqual(counts["Rule B"], 2)

    def test_none_passed_does_not_count_as_failure(self):
        reviews = [_review(checks=[_check("Rule A", "A", None)])]

        summary = build_research_summary(reviews)

        counts = {r.name: r.failures for r in summary.rule_failure_counts}
        self.assertEqual(counts["Rule A"], 0)

    def test_rule_order_follows_first_review(self):
        reviews = [
            _review(checks=[_check("Z", "Z", True), _check("A", "A", True)]),
            _review(checks=[_check("Z", "Z", False), _check("A", "A", False)]),
        ]

        summary = build_research_summary(reviews)

        self.assertEqual([r.name for r in summary.rule_failure_counts], ["Z", "A"])

    def test_most_common_failure_picks_the_highest_count(self):
        reviews = [
            _review(checks=[_check("Rule A", "A", False), _check("Rule B", "B", True)]),
            _review(checks=[_check("Rule A", "A", False), _check("Rule B", "B", False)]),
        ]

        summary = build_research_summary(reviews)

        self.assertEqual(summary.most_common_failure.name, "Rule A")
        self.assertEqual(summary.most_common_failure.failures, 2)

    def test_most_common_failure_is_none_when_nothing_ever_failed(self):
        reviews = [_review(checks=[_check("Rule A", "A", True)])]

        summary = build_research_summary(reviews)

        self.assertIsNone(summary.most_common_failure)

    def test_most_common_failure_breaks_ties_by_canonical_order(self):
        reviews = [
            _review(checks=[_check("Rule A", "A", False), _check("Rule B", "B", False)]),
        ]

        summary = build_research_summary(reviews)

        # Both fail once; "Rule A" comes first in canonical (first-review) order.
        self.assertEqual(summary.most_common_failure.name, "Rule A")

    def test_is_deterministic(self):
        reviews = [_review(), _review(signal_detected=False, failure_reason="x")]

        first = build_research_summary(reviews)
        second = build_research_summary(reviews)

        self.assertEqual(first, second)


class FormatResearchSummaryTests(unittest.TestCase):
    def test_reports_contexts_signals_and_failure_counts(self):
        summary = ResearchSummary(
            contexts_reviewed=20,
            signals_detected=0,
            rule_failure_counts=(
                RuleFailureCount("EMA Alignment", 18),
                RuleFailureCount("Impulse Gain", 20),
            ),
        )


        text = format_research_summary(summary)

        self.assertIn("Research Summary", text)
        self.assertIn("Contexts Reviewed", text)
        self.assertIn("20", text)
        self.assertIn("Signals", text)
        self.assertIn("EMA Alignment", text)
        self.assertIn("18", text)
        self.assertIn("Impulse Gain", text)
        self.assertIn("Most Common Failure", text)
        self.assertIn("20 / 20", text)

    def test_no_rules_evaluated_message_when_empty(self):

        summary = ResearchSummary(contexts_reviewed=0, signals_detected=0, rule_failure_counts=())

        text = format_research_summary(summary)

        self.assertIn("(no rules evaluated)", text)
        self.assertIn("(none)", text)

    def test_none_reported_when_no_rule_ever_failed(self):

        summary = ResearchSummary(
            contexts_reviewed=5,
            signals_detected=5,
            rule_failure_counts=(RuleFailureCount("Rule A", 0),),
        )

        text = format_research_summary(summary)

        self.assertIn("(none)", text)


class CsvExportUnaffectedByResearchFieldsTests(unittest.TestCase):
    def test_csv_export_ignores_details_and_traceability(self):
        review = _review(
            checks=[_check("Rule One", "RuleOne", True, details=[DetailItem("Sub", "x")], formula="f")],
            traceability=[DetailItem("Daily Candle", "2026-03-16")],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "review.csv"
            write_csv_export([review], path)

            with open(path, newline="") as handle:
                rows = list(csv.DictReader(handle))

            content = path.read_text()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["RuleOne"], "PASS")
        self.assertNotIn("Daily Candle", content)


if __name__ == "__main__":
    unittest.main()
