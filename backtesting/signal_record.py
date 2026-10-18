"""
Immutable, broker-independent record of one detected trading
opportunity, produced by SignalEngine (see backtesting/signal_engine.py).

A SignalRecord is a flattened projection of an Opportunity plus which
detector produced it. It intentionally carries no trade information -
no P&L, no position size, no execution state - because the Signal
Engine only validates pattern detection; it never simulates trades.

Time semantics (docs/adr/ADR-003-bar-time-semantics.md):

    timestamp             - the Opportunity's label: the open time of
                            the bar it was detected on. NOT a moment at
                            which the signal was known.
    signal_available_time - close time of that bar: the earliest moment
                            the signal exists. Any future simulator must
                            execute strictly after this, never at
                            `timestamp`.
"""

from dataclasses import dataclass
from datetime import datetime

from core.opportunity import Opportunity, OpportunityType


@dataclass(frozen=True)
class SignalRecord:
    timestamp: datetime
    symbol: str
    timeframe: str

    detector: str
    opportunity_type: OpportunityType

    entry_price: float
    stop_price: float

    confidence: float
    quality: int

    signal_available_time: datetime | None = None

    @classmethod
    def from_opportunity(
        cls,
        opportunity: Opportunity,
        detector_name: str,
        signal_available_time: datetime | None = None,
    ) -> "SignalRecord":
        """Build a SignalRecord from a detected Opportunity, tagged with
        the name of the detector that produced it and the moment the
        signal became available (see module docstring)."""
        return cls(
            timestamp=opportunity.timestamp,
            symbol=opportunity.symbol,
            timeframe=opportunity.timeframe,
            detector=detector_name,
            opportunity_type=opportunity.opportunity_type,
            entry_price=opportunity.entry_price,
            stop_price=opportunity.stop_price,
            confidence=opportunity.confidence,
            quality=opportunity.quality,
            signal_available_time=signal_available_time,
        )
