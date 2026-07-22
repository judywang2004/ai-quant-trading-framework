from dataclasses import dataclass
from enum import Enum

from .market_bias import MarketBias


class TrendStrength(Enum):
    """How much confirming evidence supports the daily bias.

    NONE   - not a viable bullish trend: EMA alignment failed, EMA20 is
             falling, or there was not enough history to evaluate at all.
    WEAK   - EMA20 > EMA50 and not falling, but the trend is borderline:
             either EMA20 is flat rather than clearly rising, or EMA
             separation is below the configured minimum.
    STRONG - EMA20 > EMA50, EMA20 is clearly rising, and EMA separation
             is sufficient.
    """

    NONE = "NONE"
    WEAK = "WEAK"
    STRONG = "STRONG"


class SlopeStatus(Enum):
    """Human-readable classification of the EMA20 slope."""

    RISING = "Rising"
    FLAT = "Flat"
    FALLING = "Falling"


@dataclass(frozen=True)
class RuleResult:
    """
    Outcome of evaluating a single objective rule.

    `passed` is a tri-state:
        True  - the rule was evaluated and satisfied.
        False - the rule was evaluated and not satisfied.
        None  - the rule is not implemented yet (e.g. Market Structure).
                Placeholder results must never be used to gate bias or
                strength.
    """

    name: str
    passed: bool | None
    detail: str


@dataclass(frozen=True)
class DailyTrendResult:
    """
    Structured result of a DailyTrendAssessment.

    `rules` holds one RuleResult per rule that was evaluated, including
    placeholders for rules not implemented yet. Adding a new rule (e.g.
    a future Market Structure rule) only adds/updates an entry here; it
    does not change this dataclass's shape or the DailyTrendAssessment
    public interface.

    Numeric fields are None when the assessment could not be computed
    (e.g. insufficient daily history).
    """

    bias: MarketBias
    strength: TrendStrength
    rules: tuple[RuleResult, ...]

    ema20: float | None
    ema50: float | None

    ema20_slope: float | None
    ema20_slope_status: SlopeStatus | None

    ema_separation: float | None
    ema_separation_pct: float | None

    explanation: str

    def rule(self, name: str) -> RuleResult | None:
        """Look up a single rule's outcome by name."""
        return next((r for r in self.rules if r.name == name), None)
