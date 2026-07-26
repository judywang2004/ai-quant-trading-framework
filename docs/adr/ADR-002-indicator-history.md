# ADR-002: Temporary Storage of Indicator History in MarketContext

**Status:** Accepted

**Date:** 2026-07-25

---

# Context

High Base Rule HB-003 requires determining whether the EMA20 is rising.

The original `MarketContext` contained only the current EMA20 value, which is insufficient to determine trend direction.

One option was to have each detector calculate EMA history internally. This was rejected because detectors should consume facts rather than calculate indicators.

Another option was to introduce a dedicated `IndicatorSeries` abstraction. While architecturally cleaner, it would introduce additional complexity before multiple detectors require historical indicator data.

---

# Decision

For Version 1, `MarketContext` includes a small, immutable `ema20_history` field containing precomputed EMA20 values supplied by the context builder.

The detector consumes this data but never computes indicator history itself.

This keeps pattern detectors deterministic and maintains the architectural principle that:

- Context Builders calculate indicators.
- MarketContext transports facts.
- Pattern Detectors interpret facts.

---

# Consequences

## Advantages

- Pattern detectors remain pure consumers of market data.
- Indicator calculations are centralized.
- No duplicated EMA calculations.
- Backward-compatible extension.
- Simple implementation suitable for MVP.

## Trade-offs

`MarketContext` now carries a limited amount of historical indicator state rather than only current values.

This is considered an acceptable compromise for Version 1.

---

# Future Direction

When multiple detectors require historical indicator sequences (EMA, ATR, RSI, MACD, etc.), introduce an `IndicatorSeries` abstraction.

A future architecture may resemble:

MarketContext
└── IndicatorSeries
    ├── ema20
    ├── ema50
    ├── atr
    └── ...

At that point, `ema20_history` can be deprecated in favor of the more general abstraction.

---

# Rationale

This decision favors simplicity for the MVP while preserving a clear migration path toward a richer indicator model as the framework evolves.