"""
Signal Engine - validates pattern detection against historical market
data.

Runs every configured PatternDetector against a sequence of
MarketContext snapshots and records every Opportunity found as a
SignalRecord (backtesting/signal_record.py). This is deliberately split
apart from full trade simulation: it lets a detector (e.g.
HighBaseDetector) be validated against history without also modeling
position sizing, risk, or execution.

The Signal Engine never simulates trades:
    - no order placement
    - no P&L
    - no position sizing
    - no exit simulation
    - no broker/API interaction

Those belong to later milestones (see backtesting/engine.py).
"""

from typing import Iterable

from core.market_context import MarketContext
from patterns.detector import PatternDetector

from backtesting.signal_record import SignalRecord


def _detector_name(detector: PatternDetector) -> str:
    """Human-readable name for a detector, for tagging SignalRecords.

    Falls back to the class name when a detector does not expose a
    `NAME` attribute - PatternDetector is a structural Protocol and does
    not require one.
    """
    return getattr(detector, "NAME", type(detector).__name__)


class SignalEngine:
    """
    Runs PatternDetectors across a sequence of MarketContexts and
    records every Opportunity produced as a SignalRecord.

    Stateless and deterministic: `run` depends only on its arguments,
    never mutates a MarketContext or Opportunity, and produces the same
    output for the same input every time.
    """

    def run(
        self,
        market_contexts: Iterable[MarketContext],
        detectors: Iterable[PatternDetector],
    ) -> list[SignalRecord]:
        detectors = list(detectors)
        records: list[SignalRecord] = []

        for context in market_contexts:
            for detector in detectors:
                opportunity = detector.detect(context)
                if opportunity is None:
                    continue

                records.append(
                    SignalRecord.from_opportunity(opportunity, _detector_name(detector))
                )

        return records
