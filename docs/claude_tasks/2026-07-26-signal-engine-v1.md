# Objective

Build the first Signal Engine of the AI Quant Trading Framework.

This component scans historical market data, builds MarketContext objects, executes pattern detectors, and records detected trading opportunities.

The Signal Engine does **not** simulate trades.

Its sole responsibility is to validate pattern detection.

---

# Background

The Foundation Layer is complete.

Completed components:

- DailyAssessment
- MarketContext
- Pattern Framework
- HighBaseDetector
- Opportunity
- PositionSizer
- OrderRequest

The next step is verifying that the detector produces meaningful trading signals on historical data.

Trade simulation is intentionally deferred.

---

# Responsibilities

The Signal Engine shall:

1. Read historical OHLCV data.
2. Build a MarketContext for each completed candle.
3. Execute one or more PatternDetectors.
4. Record every Opportunity returned.
5. Produce a deterministic list of detected signals.

The engine shall NOT:

- place orders
- calculate P&L
- calculate position sizes
- simulate exits
- communicate with brokers

---

# Architecture

Historical Data
        │
        ▼
MarketContext Builder
        │
        ▼
Signal Engine
        │
        ▼
Pattern Detector(s)
        │
        ▼
Opportunity
        │
        ▼
Signal Record

---

# Suggested Structure

backtesting/
    signal_engine.py
    signal_record.py

tests/
    test_signal_engine.py

examples/
    demo_signal_engine.py

---

# SignalRecord

Create a lightweight immutable record.

Suggested fields:

- timestamp
- symbol
- timeframe
- detector
- opportunity_type
- entry_price
- stop_price
- confidence
- quality

No trade information.

---

# SignalEngine

Suggested interface:

```python
run(
    market_contexts: Iterable[MarketContext],
    detectors: Iterable[PatternDetector],
) -> list[SignalRecord]
```

Responsibilities:

For each MarketContext:

Run every detector.

If detector returns Opportunity:

Create SignalRecord.

Append to results.

Continue.

No mutation.

Deterministic execution.

---

# Design Principles

Signal Engine must:

- remain broker independent
- remain deterministic
- never modify MarketContext
- never modify Opportunity
- support multiple detectors

---

# Out of Scope

Do not implement:

- trade simulation
- order execution
- risk management
- portfolio
- commissions
- slippage
- statistics
- equity curve

Those belong to later milestones.

---

# Deliverables

backtesting/signal_engine.py

backtesting/signal_record.py

Unit tests

Example usage

---

# Acceptance Criteria

Signal Engine accepts:

- MarketContext sequence
- Detector sequence

Returns:

list[SignalRecord]

Supports:

zero detectors

multiple detectors

zero signals

multiple signals

All existing tests continue to pass.

No MT4/MT5 dependencies.

No broker-specific code.
