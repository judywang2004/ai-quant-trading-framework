"""
Broker- and pattern-independent representation of a candidate trading
setup.

An Opportunity is created once a lower-timeframe component (e.g. an H1
pullback detector, not yet implemented) starts tracking a candidate
setup, and is updated as that setup matures through PatternState. It is
deliberately generic: it says *what kind* of setup this is and *what
state* it is in, but contains no pattern-specific detection logic (e.g.
no High Base rules live here). Pattern detectors return Opportunity
objects rather than a bare True/False, so every future detector (High
Base, Pullback, EMA Ride, ...) shares this one interface.

This sits upstream of models.signal.Signal in the strategy workflow: a
Signal is a ready-to-execute decision (entry/stop/take-profit); an
Opportunity is a candidate the strategy is still watching that may or
may not ever produce one.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from models.market_bias import MarketBias


class OpportunityType(Enum):
    """
    Kind of setup being tracked. Mirrors the pattern categories in
    research/market_knowledge/.

    FAILED_BREAKOUT is a reserved placeholder: today it only labels an
    outcome in the knowledge base, but a failed breakout can itself
    become a tradeable setup (e.g. fading it) in a future strategy.
    No detector produces it yet.
    """

    HIGH_BASE = "HIGH_BASE"
    PULLBACK = "PULLBACK"
    EMA_RIDE = "EMA_RIDE"
    FLAG = "FLAG"
    FAILED_BREAKOUT = "FAILED_BREAKOUT"


class PatternState(Enum):
    """Lifecycle of a tracked Opportunity."""

    FORMING = "FORMING"          # still developing; objective criteria not yet met
    READY = "READY"              # objective criteria met; actionable, tradeable setup
    TRIGGERED = "TRIGGERED"      # an entry trigger fired on a lower timeframe
    COMPLETED = "COMPLETED"      # triggered and the resulting trade has run its course
    INVALIDATED = "INVALIDATED"  # broke down, or timed out, before completing


@dataclass(frozen=True)
class Opportunity:
    """
    A candidate trading setup identified on a given symbol/timeframe.

    `entry_price` and `stop_price` are the two structural price levels
    every setup type has, whatever its specific detection rules: the
    level that defines the setup (e.g. a base's breakout level) and the
    level beyond which it is no longer valid. Naming them the same as
    the fields PositionSizer and OrderRequest use means no translation
    layer is needed to turn an Opportunity into an order.

    `confidence` is a statistical/model-driven score in [0.0, 1.0],
    intended so a future rule-based scorer or ML model can populate the
    same field without changing this data model. `quality` is a
    separate, coarser 1-5 qualitative rating (e.g. dashboard ranking,
    strategy filtering) that is independent of confidence - a setup can
    be textbook-quality (5) with model confidence still uncertain, or
    vice versa.
    """

    symbol: str
    timeframe: str
    timestamp: datetime

    opportunity_type: OpportunityType
    state: PatternState
    bias: MarketBias

    entry_price: float
    stop_price: float

    strategy_name: str

    quality: int = 3
    confidence: float = 1.0
    notes: str = ""

    def __post_init__(self):
        if not 1 <= self.quality <= 5:
            raise ValueError("quality must be between 1 and 5")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
