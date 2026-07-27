"""
Generic, detector-agnostic data model for validation and research
reviews: one MarketContext evaluated rule-by-rule against one detector,
for manual comparison against a real chart (e.g. TradingView).

This module knows nothing about High Base, Flag, Cup & Handle, or any
other specific pattern - that knowledge lives entirely in a per-detector
"explainer" (see validation/explainers.py). validation_formatter.py and
demo_signal_engine.py only ever consume the generic shapes defined here
(RuleCheck, ContextReview, DatasetSummary, ResearchSummary), so a future
detector can plug into the same review/export/research pipeline by
providing its own explainer, without any of those modules changing.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable


@dataclass(frozen=True)
class DetailItem:
    """
    One extra, structured research-mode fact attached to a RuleCheck or
    a ContextReview - e.g. a sub-rule of a composite check ("Alignment
    Rule: EMA20 > EMA50 -> PASS"), a raw indicator value ("EMA20:
    159.24618"), or a traced input candle ("H1 Candle: 2026-03-17
    04:00").

    `status`, when not None, renders as an inline PASS/FAIL next to the
    value - used for sub-rules that have their own pass/fail outcome
    distinct from the parent RuleCheck's overall `passed`.
    """

    label: str
    value: str
    status: bool | None = None


@dataclass(frozen=True)
class RuleCheck:
    """
    One human-readable rule evaluated as part of a review.

    `passed` is tri-state:
        True  - the rule was evaluated and satisfied.
        False - the rule was evaluated and not satisfied.
        None  - the rule could not be evaluated (e.g. insufficient
                candle history). None must never be reported as PASS
                or FAIL.

    `column` is a short, spreadsheet-friendly header (e.g.
    "ImpulseGain") used only by CSV export; `name` is the descriptive
    label (e.g. "Impulse Gain") used in the console report.

    `formula`, `expected_label`, and `details` are research-mode-only
    extras: review mode (format_console_review) ignores them entirely,
    so an explainer can add richer detail for --research without ever
    affecting the concise --review output. `expected_label` lets an
    explainer relabel the threshold line (e.g. "Required" instead of
    "Threshold") without the formatter needing to know why.
    """

    name: str
    column: str
    passed: bool | None
    expected: str = ""
    actual: str = ""
    formula: str = ""
    expected_label: str = "Threshold"
    details: tuple[DetailItem, ...] = ()

    def __post_init__(self):
        if not isinstance(self.details, tuple):
            object.__setattr__(self, "details", tuple(self.details))


@dataclass(frozen=True)
class ContextReview:
    """
    Full rule-by-rule validation review of one MarketContext against
    one detector.

    `pattern_label` is the human-readable pattern name (e.g. "High
    Base") used for report headings and the manual review checklist -
    kept as data here, rather than hardcoded in validation_formatter.py,
    so the formatter stays usable for any future detector's explainer.

    `traceability` identifies every raw candle the decision was based
    on (e.g. "Daily Candle" / "H1 Candle"), so a researcher can replay
    the exact same candles in TradingView. Research-mode-only, like
    RuleCheck's extras above - ignored by format_console_review.
    """

    timestamp: datetime
    symbol: str
    timeframe: str
    detector: str
    pattern_label: str

    checks: tuple[RuleCheck, ...]

    signal_detected: bool
    failure_reason: str = ""
    traceability: tuple[DetailItem, ...] = ()

    def __post_init__(self):
        if not isinstance(self.checks, tuple):
            object.__setattr__(self, "checks", tuple(self.checks))
        if not isinstance(self.traceability, tuple):
            object.__setattr__(self, "traceability", tuple(self.traceability))


@dataclass(frozen=True)
class DatasetSummary:
    """
    Describes the dataset a batch of ContextReviews was drawn from, and
    how --start/--end/--limit narrowed it down to the contexts actually
    reviewed - printed once, at the top of a research report, so a
    researcher is never confused about what date range they're looking
    at (see demo_signal_engine.py's --research mode).
    """

    first_context_timestamp: datetime | None
    last_context_timestamp: datetime | None
    contexts_available: int
    requested_start: date | None
    requested_end: date | None
    contexts_selected: int


@dataclass(frozen=True)
class RuleFailureCount:
    """How many reviewed contexts a given rule (by name) failed in."""

    name: str
    failures: int


@dataclass(frozen=True)
class ResearchSummary:
    """
    Aggregate statistics across a batch of ContextReviews, so a
    researcher can spot the bottleneck rule at a glance instead of
    reading every individual review.

    Only ever reads RuleCheck.name/passed and ContextReview.
    signal_detected - stays detector-agnostic the same way
    ContextReview itself does.
    """

    contexts_reviewed: int
    signals_detected: int
    rule_failure_counts: tuple[RuleFailureCount, ...]

    @property
    def most_common_failure(self) -> RuleFailureCount | None:
        """The rule with the most failures, or None if no rule ever
        failed (e.g. every context was reviewed with 0 rules, or every
        rule passed everywhere)."""
        candidates = [r for r in self.rule_failure_counts if r.failures > 0]
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.failures)


def build_research_summary(reviews: Iterable[ContextReview]) -> ResearchSummary:
    """
    Aggregate a batch of ContextReviews into a ResearchSummary.

    Rule order in `rule_failure_counts` follows the first review's own
    check order - every review in a single run comes from the same
    explainer, so all reviews share the same ordered set of rule names
    (the same assumption validation_formatter.write_csv_export already
    makes for its CSV columns).
    """
    reviews = list(reviews)
    contexts_reviewed = len(reviews)
    signals_detected = sum(1 for review in reviews if review.signal_detected)

    rule_names = [check.name for check in reviews[0].checks] if reviews else []
    failure_counts = dict.fromkeys(rule_names, 0)

    for review in reviews:
        for check in review.checks:
            if check.passed is False:
                failure_counts[check.name] = failure_counts.get(check.name, 0) + 1

    rule_failure_counts = tuple(
        RuleFailureCount(name=name, failures=failure_counts[name]) for name in rule_names
    )

    return ResearchSummary(
        contexts_reviewed=contexts_reviewed,
        signals_detected=signals_detected,
        rule_failure_counts=rule_failure_counts,
    )
