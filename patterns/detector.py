"""
Structural contract every pattern detector satisfies.

This is intentionally a Protocol, not an abstract base class: the
contract is behavioral (has a matching `detect` method), not
hierarchical. A detector never needs to inherit from anything here -
any object with a matching `detect` method already satisfies
PatternDetector. That lets HighBaseDetector, PullbackDetector,
EMARideDetector, FlagDetector, etc. be added independently, without
this module changing.

Detectors are read-only observers of MarketContext:

    - they read MarketContext, never modify it
    - they never calculate risk or position size
    - they never place orders or talk to a broker
    - they only recognize market structure and, if found, describe it
      as an Opportunity

No boolean returns: a detector reports either a concrete Opportunity or
None ("nothing recognized here"), never True/False.
"""

from typing import Protocol, runtime_checkable

from core.market_context import MarketContext
from core.opportunity import Opportunity


@runtime_checkable
class PatternDetector(Protocol):
    def detect(self, context: MarketContext) -> Opportunity | None:
        """
        Inspect `context` and return an Opportunity if the pattern this
        detector recognizes is present, or None otherwise.

        Returning None is the normal, expected outcome when nothing is
        found - it is not an error condition.
        """
        ...
