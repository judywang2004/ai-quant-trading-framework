# Objective

Design and implement the immutable MarketContext object.

MarketContext will become the single source of truth for all market information required by pattern detectors.

Every detector should consume a MarketContext instead of independently calculating indicators or reading raw OHLC data.

No trading logic should be implemented in this task.

---

# Background

The Trading Engine interfaces (Opportunity, PositionSizer, OrderRequest) are now stable.

The next architectural layer is the input side of the engine.

MarketContext provides a consistent, reusable interface between market data and pattern detection.

Future detectors such as:

- HighBaseDetector
- PullbackDetector
- EMARideDetector

must all receive the same MarketContext instance.

This avoids duplicated calculations and ensures consistency between:

- Python backtests
- MT4
- MT5
- Future live execution

---

# Requirements

Create:

core/market_context.py

The MarketContext should be implemented as an immutable dataclass.

Recommended fields:

- symbol
- timeframe
- timestamp
- candles
- ema20
- ema50
- atr
- daily_assessment

The class should only contain market state.

It must not contain:

- trading signals
- opportunities
- execution logic
- risk management

---

# Design Principles

MarketContext represents facts.

It should never represent decisions.

Examples:

Correct:

EMA20 = 154.23

ATR = 0.84

Daily Trend = STRONG

Incorrect:

Buy Signal

High Base Found

Risk = 0.5%

Those belong to later pipeline stages.

---

# Out of Scope

Do not implement:

- Pattern detection
- Indicator calculation
- EMA calculation
- ATR calculation

MarketContext receives these values.

It does not compute them.

---

# Deliverables

- core/market_context.py
- Unit tests
- Type hints
- Documentation

---

# Acceptance Criteria

MarketContext is immutable.

No broker dependency exists.

No MT4/MT5 code exists.

All existing tests continue to pass.

The object is ready to be consumed by future pattern detectors.