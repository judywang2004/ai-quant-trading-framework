"""
Immutable, broker-independent record of one detected trading
opportunity, produced by SignalEngine (see backtesting/signal_engine.py).

A SignalRecord is a flattened projection of an Opportunity plus which
detector produced it. It intentionally carries no trade information -
no P&L, no position size, no execution state - because the Signal
Engine only validates pattern detection; it never simulates trades.
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

    @classmethod
    def from_opportunity(cls, opportunity: Opportunity, detector_name: str) -> "SignalRecord":
        """Build a SignalRecord from a detected Opportunity, tagged with
        the name of the detector that produced it."""
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
        )
