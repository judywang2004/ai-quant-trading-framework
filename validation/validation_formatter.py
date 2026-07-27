"""
Renders ContextReview objects (validation/validation_report.py) either
as a human-readable console block for manual comparison against
TradingView, or as a CSV row for bulk review in a spreadsheet.

Detector-agnostic: this module only ever reads the generic
RuleCheck/ContextReview shape a detector's explainer (see
validation/explainers.py) produces. Adding a new detector's explainer
never requires a change here.
"""

import csv
from typing import Iterable, TextIO

from validation.validation_report import ContextReview, DatasetSummary, ResearchSummary, RuleCheck

SECTION = "=" * 60
DIVIDER = "-" * 60

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M"

# TradingView's own interval labels differ from this project's internal
# timeframe codes (e.g. "H1" -> "1H"). Detector logic and MarketContext
# never need to know about this - it exists purely so a human reviewer
# can type the right interval into TradingView. Falls back to the
# internal code itself for any timeframe not listed.
_TRADINGVIEW_INTERVALS = {
    "D1": "1D",
    "H1": "1H",
    "M15": "15",
    "M5": "5",
}

BASE_CSV_FIELDS = ["Timestamp", "Symbol", "Timeframe"]
TRAILING_CSV_FIELDS = ["Result", "FailureReason"]


def _status_label(passed: bool | None) -> str:
    if passed is None:
        return "N/A"
    return "PASS" if passed else "FAIL"


def _format_check(check: RuleCheck) -> list[str]:
    lines = [check.name, ""]

    if check.expected:
        lines += ["Expected:", check.expected, ""]
    if check.actual:
        lines += ["Actual:", check.actual, ""]

    lines.append(_status_label(check.passed))
    return lines


def format_console_review(review: ContextReview, index: int, total: int) -> str:
    """Render one ContextReview as a full, human-readable review block,
    suitable for comparing side by side with a TradingView chart.

    Ends with a "Manual TradingView Review" checklist for the human
    reviewer to fill in by hand - intentionally not part of
    ContextReview's data and never written by write_csv_export().
    """
    timestamp_str = review.timestamp.strftime(TIMESTAMP_FORMAT)
    tradingview_interval = _TRADINGVIEW_INTERVALS.get(review.timeframe, review.timeframe)

    lines = [
        SECTION,
        f"Review {index} / {total}",
        SECTION,
        "",
        "Symbol:",
        review.symbol,
        "",
        "Timeframe:",
        review.timeframe,
        "",
        "Timestamp:",
        timestamp_str,
        "",
        DIVIDER,
        "TradingView",
        DIVIDER,
        "",
        "Ticker:",
        review.symbol,
        "",
        "Timeframe:",
        tradingview_interval,
        "",
        "Go to candle:",
        timestamp_str,
        "",
        DIVIDER,
        f"{review.pattern_label} Evaluation",
        DIVIDER,
        "",
    ]

    for check in review.checks:
        lines.extend(_format_check(check))
        lines.append("")
        lines.append(DIVIDER)
        lines.append("")

    lines.append("FINAL RESULT")
    lines.append("")
    lines.append("SIGNAL DETECTED" if review.signal_detected else "NO SIGNAL")
    lines.append("")

    if review.failure_reason:
        lines += ["Reason", "", review.failure_reason, ""]

    lines += [
        DIVIDER,
        "",
        "Manual TradingView Review",
        "",
        f"[ ] Looks like a valid {review.pattern_label}",
        "",
        f"[ ] Not a {review.pattern_label}",
        "",
        "[ ] Unsure",
        "",
        "Notes:",
        "",
        "_" * 40,
    ]

    return "\n".join(lines)


def _csv_fieldnames(reviews: list[ContextReview]) -> list[str]:
    check_columns = [check.column for check in reviews[0].checks] if reviews else []
    return BASE_CSV_FIELDS + check_columns + TRAILING_CSV_FIELDS


def _csv_row(review: ContextReview) -> dict[str, str]:
    row = {
        "Timestamp": review.timestamp.strftime(TIMESTAMP_FORMAT),
        "Symbol": review.symbol,
        "Timeframe": review.timeframe,
        "Result": "SIGNAL" if review.signal_detected else "NO SIGNAL",
        "FailureReason": review.failure_reason,
    }
    row.update({check.column: _status_label(check.passed) for check in review.checks})
    return row


def write_csv_export(reviews: Iterable[ContextReview], path) -> None:
    """Write one CSV row per ContextReview: PASS/FAIL/N/A per rule
    check, plus the overall Result and FailureReason.

    The manual human-review checklist (see format_console_review) is
    intentionally console-only and never written here.

    Assumes every review came from the same explainer, so all share the
    same ordered set of rule-check columns - true for any single
    demo_signal_engine.py invocation, which runs one detector.
    """
    reviews = list(reviews)
    fieldnames = _csv_fieldnames(reviews)

    with open(path, "w", newline="") as handle:
        _write_csv(handle, reviews, fieldnames)


def _write_csv(handle: TextIO, reviews: list[ContextReview], fieldnames: list[str]) -> None:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for review in reviews:
        writer.writerow(_csv_row(review))


# ------------------------------------------------------------------
# Research mode: a much more detailed, engineering-grade report -
# every intermediate value, formula, and sub-rule outcome behind each
# PASS/FAIL, so a researcher can verify every calculation by hand
# against TradingView. Still fully detector-agnostic: only ever reads
# RuleCheck/ContextReview/DatasetSummary/ResearchSummary fields.
# ------------------------------------------------------------------


def _format_detail_item(item) -> list[str]:
    lines = [item.label, item.value]
    if item.status is not None:
        lines.append(_status_label(item.status))
    lines.append("")
    return lines


def _format_research_check(check: RuleCheck) -> list[str]:
    lines = [DIVIDER, check.name, "", "Decision", _status_label(check.passed), ""]

    if check.details:
        # A composite check (e.g. one that unpacks a whole sub-assessment
        # into its own sub-rules, each with its own PASS/FAIL) tells its
        # full story through `details` alone - printing formula/expected/
        # actual afterwards would just repeat its own final line.
        for detail in check.details:
            lines.extend(_format_detail_item(detail))
        return lines

    if check.formula:
        lines += ["Formula", check.formula, ""]

    if check.expected:
        lines += [check.expected_label, check.expected, ""]

    if check.actual:
        lines += ["Actual", check.actual, ""]

    return lines


def format_research_review(review: ContextReview, index: int, total: int) -> str:
    """Render one ContextReview as a detailed engineering report: every
    rule's raw values, thresholds, formulas, and sub-rule outcomes, plus
    a Traceability section identifying every candle used - everything
    needed to replay and verify the decision in TradingView by hand."""
    timestamp_str = review.timestamp.strftime(TIMESTAMP_FORMAT)
    tradingview_interval = _TRADINGVIEW_INTERVALS.get(review.timeframe, review.timeframe)

    lines = [
        SECTION,
        f"Research Review {index} / {total}",
        SECTION,
        "",
        "Symbol:",
        review.symbol,
        "",
        "Timeframe:",
        review.timeframe,
        "",
        "Timestamp:",
        timestamp_str,
        "",
        DIVIDER,
        "TradingView",
        DIVIDER,
        "",
        "Ticker:",
        review.symbol,
        "",
        "Timeframe:",
        tradingview_interval,
        "",
        "Go to candle:",
        timestamp_str,
        "",
    ]

    if review.traceability:
        lines += [DIVIDER, "Traceability", DIVIDER, ""]
        for item in review.traceability:
            lines.extend(_format_detail_item(item))

    lines += [DIVIDER, f"{review.pattern_label} Evaluation (Detailed)", ""]

    for check in review.checks:
        lines.extend(_format_research_check(check))

    lines += [
        DIVIDER,
        "",
        "FINAL RESULT",
        "",
        "SIGNAL DETECTED" if review.signal_detected else "NO SIGNAL",
        "",
    ]

    if review.failure_reason:
        lines += ["Reason", "", review.failure_reason, ""]

    return "\n".join(lines)


def format_dataset_summary(summary: DatasetSummary) -> str:
    """Render dataset/filter context at the top of a research report, so
    a researcher is never confused about what range of data --start/
    --end/--limit actually selected."""
    first = summary.first_context_timestamp.strftime(TIMESTAMP_FORMAT) if summary.first_context_timestamp else "N/A"
    last = summary.last_context_timestamp.strftime(TIMESTAMP_FORMAT) if summary.last_context_timestamp else "N/A"
    requested_start = summary.requested_start if summary.requested_start is not None else "(unbounded)"
    requested_end = summary.requested_end if summary.requested_end is not None else "(unbounded)"

    lines = [
        SECTION,
        "Dataset",
        SECTION,
        "",
        "First Context",
        first,
        "",
        "Last Context",
        last,
        "",
        "Contexts Available",
        str(summary.contexts_available),
        "",
        "Requested Range",
        f"{requested_start} to {requested_end}",
        "",
        "Contexts Selected",
        str(summary.contexts_selected),
    ]
    return "\n".join(lines)


def format_research_summary(summary: ResearchSummary) -> str:
    """Render aggregate rule-failure statistics across a batch of
    reviews, so a researcher can spot the bottleneck rule without
    reading every individual review."""
    lines = [
        SECTION,
        "Research Summary",
        SECTION,
        "",
        "Contexts Reviewed",
        str(summary.contexts_reviewed),
        "",
        "Signals",
        str(summary.signals_detected),
        "",
        "Rule Failure Counts",
        "",
    ]

    if summary.rule_failure_counts:
        for rule in summary.rule_failure_counts:
            lines += [rule.name, str(rule.failures), ""]
    else:
        lines += ["(no rules evaluated)", ""]

    lines.append("Most Common Failure")
    lines.append("")

    most_common = summary.most_common_failure
    if most_common is None:
        lines.append("(none)")
    else:
        lines.append(most_common.name)
        lines.append(f"{most_common.failures} / {summary.contexts_reviewed}")

    return "\n".join(lines)
