import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from validation.validation_formatter import format_console_review, write_csv_export, write_csv_review_export
from validation.validation_report import ContextReview, RuleCheck

# Deliberately NOT High Base specific: proves the formatter is generic
# and would work unchanged for a future detector's own explainer.
FAKE_PATTERN = "Test Pattern"
FAKE_DETECTOR = "FakeDetector"


def _check(name, column, passed, expected="exp", actual="act") -> RuleCheck:
    return RuleCheck(name=name, column=column, passed=passed, expected=expected, actual=actual)


def _review(signal_detected=True, failure_reason="", checks=None, timeframe="H1") -> ContextReview:
    return ContextReview(
        timestamp=datetime(2025, 3, 12, 8, 0),
        symbol="USDJPY",
        timeframe=timeframe,
        detector=FAKE_DETECTOR,
        pattern_label=FAKE_PATTERN,
        checks=tuple(checks) if checks is not None else (
            _check("Rule One", "RuleOne", True),
            _check("Rule Two", "RuleTwo", False),
        ),
        signal_detected=signal_detected,
        failure_reason=failure_reason,
    )


class FormatConsoleReviewTests(unittest.TestCase):
    def test_contains_identity_and_tradingview_sections(self):
        text = format_console_review(_review(), index=7, total=20)

        self.assertIn("Review 7 / 20", text)
        self.assertIn("Symbol:", text)
        self.assertIn("USDJPY", text)
        self.assertIn("Timeframe:\nH1", text)
        self.assertIn("Timestamp:\n2025-03-12 08:00", text)
        self.assertIn("TradingView", text)
        self.assertIn("Ticker:", text)
        self.assertIn("Go to candle:", text)

    def test_maps_internal_timeframe_to_tradingview_interval(self):
        text = format_console_review(_review(timeframe="H1"), index=1, total=1)

        self.assertIn("1H", text)

    def test_unmapped_timeframe_falls_back_to_itself(self):
        text = format_console_review(_review(timeframe="W1"), index=1, total=1)

        self.assertIn("W1", text)

    def test_evaluation_section_uses_pattern_label(self):
        text = format_console_review(_review(), index=1, total=1)

        self.assertIn(f"{FAKE_PATTERN} Evaluation", text)

    def test_each_check_reports_name_expected_actual_and_status(self):
        checks = [_check("Rule One", "RuleOne", True, expected="X", actual="Y")]
        text = format_console_review(_review(checks=checks), index=1, total=1)

        self.assertIn("Rule One", text)
        self.assertIn("Expected:\nX", text)
        self.assertIn("Actual:\nY", text)
        self.assertIn("PASS", text)

    def test_check_with_no_passed_value_reports_na(self):
        checks = [_check("Rule One", "RuleOne", None)]
        text = format_console_review(_review(checks=checks, signal_detected=False), index=1, total=1)

        self.assertIn("N/A", text)

    def test_signal_detected_shows_signal_and_no_reason_section(self):
        text = format_console_review(_review(signal_detected=True, failure_reason=""), index=1, total=1)

        self.assertIn("FINAL RESULT", text)
        self.assertIn("SIGNAL DETECTED", text)
        self.assertNotIn("Reason", text)

    def test_no_signal_shows_reason(self):
        text = format_console_review(
            _review(signal_detected=False, failure_reason="Impulse too weak."), index=1, total=1
        )

        self.assertIn("NO SIGNAL", text)
        self.assertIn("Reason", text)
        self.assertIn("Impulse too weak.", text)

    def test_manual_review_checklist_uses_pattern_label(self):
        text = format_console_review(_review(), index=1, total=1)

        self.assertIn("Manual TradingView Review", text)
        self.assertIn(f"[ ] Looks like a valid {FAKE_PATTERN}", text)
        self.assertIn(f"[ ] Not a {FAKE_PATTERN}", text)
        self.assertIn("[ ] Unsure", text)
        self.assertIn("Notes:", text)

    def test_output_is_deterministic(self):
        review = _review()

        first = format_console_review(review, index=1, total=1)
        second = format_console_review(review, index=1, total=1)

        self.assertEqual(first, second)


class WriteCsvExportTests(unittest.TestCase):
    def _read_rows(self, path):
        with open(path, newline="") as handle:
            return list(csv.DictReader(handle))

    def test_header_and_row_values(self):
        checks = [
            _check("Rule One", "RuleOne", True),
            _check("Rule Two", "RuleTwo", False),
            _check("Rule Three", "RuleThree", None),
        ]
        review = _review(
            signal_detected=False, failure_reason="Rule Two failed.", checks=checks
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "review.csv"
            write_csv_export([review], path)

            rows = self._read_rows(path)
            with open(path, newline="") as handle:
                header = next(csv.reader(handle))

        self.assertEqual(
            header,
            ["Timestamp", "Symbol", "Timeframe", "RuleOne", "RuleTwo", "RuleThree", "Result", "FailureReason"],
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["Timestamp"], "2025-03-12 08:00")
        self.assertEqual(row["Symbol"], "USDJPY")
        self.assertEqual(row["Timeframe"], "H1")
        self.assertEqual(row["RuleOne"], "PASS")
        self.assertEqual(row["RuleTwo"], "FAIL")
        self.assertEqual(row["RuleThree"], "N/A")
        self.assertEqual(row["Result"], "NO SIGNAL")
        self.assertEqual(row["FailureReason"], "Rule Two failed.")

    def test_signal_detected_row_reports_signal_result(self):
        review = _review(signal_detected=True, failure_reason="")

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "review.csv"
            write_csv_export([review], path)
            rows = self._read_rows(path)

        self.assertEqual(rows[0]["Result"], "SIGNAL")
        self.assertEqual(rows[0]["FailureReason"], "")

    def test_never_exports_manual_review_section(self):
        review = _review()

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "review.csv"
            write_csv_export([review], path)
            content = path.read_text()

        self.assertNotIn("Manual", content)
        self.assertNotIn("Looks like a valid", content)

    def test_empty_reviews_writes_header_only(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "review.csv"
            write_csv_export([], path)

            with open(path, newline="") as handle:
                header = next(csv.reader(handle))
            rows = self._read_rows(path)

        self.assertEqual(header, ["Timestamp", "Symbol", "Timeframe", "Result", "FailureReason"])
        self.assertEqual(rows, [])

    def test_multiple_reviews_produce_one_row_each(self):
        reviews = [_review(), _review(signal_detected=False, failure_reason="x")]

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "review.csv"
            write_csv_export(reviews, path)
            rows = self._read_rows(path)

        self.assertEqual(len(rows), 2)


class WriteCsvReviewExportTests(unittest.TestCase):
    """Covers write_csv_review_export - the lean 'golden dataset' CSV
    for a manual validation study (Task 731), distinct from
    write_csv_export's full per-rule audit CSV."""

    def _read_rows(self, path):
        with open(path, newline="") as handle:
            return list(csv.DictReader(handle))

    def _header(self, path):
        with open(path, newline="") as handle:
            return next(csv.reader(handle))

    def test_header_matches_golden_dataset_schema_for_chosen_columns(self):
        review = _review(
            checks=[
                _check("Daily Trend Assessment", "DailyTrend", True),
                _check("EMA Alignment", "EMAAlignment", False),
                _check("Impulse Gain", "ImpulseGain", False),
                _check("Base Width", "BaseWidth", True),
                _check("Breakout", "Breakout", False),
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "golden.csv"
            write_csv_review_export(
                [review], path, columns=["DailyTrend", "EMAAlignment", "ImpulseGain", "BaseWidth", "Breakout"]
            )
            header = self._header(path)

        self.assertEqual(
            header,
            [
                "Timestamp",
                "Symbol",
                "Timeframe",
                "DetectorDecision",
                "DailyTrend",
                "EMAAlignment",
                "ImpulseGain",
                "BaseWidth",
                "Breakout",
                "HumanDecision",
                "Notes",
            ],
        )

    def test_row_values_reflect_review_and_omits_unselected_columns(self):
        # "Rule Two" exists on the review but is not in `columns` - it
        # must not leak into the CSV.
        checks = [
            _check("Rule One", "RuleOne", True),
            _check("Rule Two", "RuleTwo", False),
        ]
        review = _review(signal_detected=False, checks=checks)

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "golden.csv"
            write_csv_review_export([review], path, columns=["RuleOne"])
            header = self._header(path)
            rows = self._read_rows(path)

        self.assertNotIn("RuleTwo", header)
        row = rows[0]
        self.assertEqual(row["Timestamp"], "2025-03-12 08:00")
        self.assertEqual(row["Symbol"], "USDJPY")
        self.assertEqual(row["Timeframe"], "H1")
        self.assertEqual(row["DetectorDecision"], "NO SIGNAL")
        self.assertEqual(row["RuleOne"], "PASS")

    def test_signal_detected_reports_signal_decision(self):
        review = _review(signal_detected=True, checks=[_check("RuleOne", "RuleOne", True)])

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "golden.csv"
            write_csv_review_export([review], path, columns=["RuleOne"])
            rows = self._read_rows(path)

        self.assertEqual(rows[0]["DetectorDecision"], "SIGNAL")

    def test_human_decision_and_notes_are_always_blank(self):
        review = _review(checks=[_check("RuleOne", "RuleOne", True)])

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "golden.csv"
            write_csv_review_export([review], path, columns=["RuleOne"])
            rows = self._read_rows(path)

        self.assertEqual(rows[0]["HumanDecision"], "")
        self.assertEqual(rows[0]["Notes"], "")

    def test_none_passed_renders_as_na(self):
        review = _review(checks=[_check("RuleOne", "RuleOne", None)])

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "golden.csv"
            write_csv_review_export([review], path, columns=["RuleOne"])
            rows = self._read_rows(path)

        self.assertEqual(rows[0]["RuleOne"], "N/A")

    def test_missing_column_on_a_review_renders_blank_not_an_error(self):
        # e.g. mixing detectors whose checks don't all share every
        # column - should degrade gracefully rather than raise.
        review = _review(checks=[_check("RuleOne", "RuleOne", True)])

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "golden.csv"
            write_csv_review_export([review], path, columns=["RuleOne", "RuleTwo"])
            rows = self._read_rows(path)

        self.assertEqual(rows[0]["RuleTwo"], "")

    def test_columns_defaults_to_every_check_column_when_not_given(self):
        review = _review(
            checks=[_check("Rule One", "RuleOne", True), _check("Rule Two", "RuleTwo", False)]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "golden.csv"
            write_csv_review_export([review], path)
            header = self._header(path)

        self.assertIn("RuleOne", header)
        self.assertIn("RuleTwo", header)

    def test_multiple_reviews_produce_one_row_each(self):
        reviews = [
            _review(checks=[_check("RuleOne", "RuleOne", True)]),
            _review(signal_detected=False, checks=[_check("RuleOne", "RuleOne", False)]),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "golden.csv"
            write_csv_review_export(reviews, path, columns=["RuleOne"])
            rows = self._read_rows(path)

        self.assertEqual(len(rows), 2)

    def test_empty_reviews_writes_header_only(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "golden.csv"
            write_csv_review_export([], path, columns=["DailyTrend"])

            header = self._header(path)
            rows = self._read_rows(path)

        self.assertEqual(
            header,
            ["Timestamp", "Symbol", "Timeframe", "DetectorDecision", "DailyTrend", "HumanDecision", "Notes"],
        )
        self.assertEqual(rows, [])

    def test_empty_reviews_and_no_columns_writes_minimal_header(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "golden.csv"
            write_csv_review_export([], path)

            header = self._header(path)

        self.assertEqual(
            header, ["Timestamp", "Symbol", "Timeframe", "DetectorDecision", "HumanDecision", "Notes"]
        )

    def test_never_includes_failure_reason_or_manual_review_checklist(self):
        review = _review(signal_detected=False, failure_reason="Impulse too weak.")

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "golden.csv"
            write_csv_review_export([review], path, columns=["RuleOne", "RuleTwo"])
            content = path.read_text()

        self.assertNotIn("Impulse too weak.", content)
        self.assertNotIn("Manual TradingView Review", content)


if __name__ == "__main__":
    unittest.main()
