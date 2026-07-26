# Objective

Create the Pattern Framework that will serve as the foundation for every future market pattern.

This task intentionally focuses on architecture rather than trading logic.

The objective is to establish a consistent contract for pattern detection without implementing complete High Base detection rules.

---

# Background

The Foundation Layer is now complete.

Completed components:

- DailyAssessment
- MarketContext
- Opportunity
- PositionSizer
- OrderRequest

The next layer is Pattern Intelligence.

Every future detector should consume MarketContext and produce an Opportunity.

Examples include:

- HighBaseDetector
- PullbackDetector
- EMARideDetector
- FlagDetector

---

# Requirements

Create a new package:

patterns/

Recommended initial structure:

patterns/
    __init__.py
    detector.py
    high_base_detector.py

---

# Pattern Detection Contract

Instead of creating an abstract base class, define a lightweight protocol representing the detector contract.

A detector must expose:

```python
detect(context: MarketContext) -> Opportunity | None
```

No inheritance is required.

The purpose is to define behavior rather than implementation.

Future detectors should naturally satisfy this contract.

---

# HighBaseDetector Skeleton

Implement the initial detector skeleton.

Responsibilities:

- Accept MarketContext
- Perform basic validation
- Return None when detection conditions are not met
- Produce an Opportunity object only when a valid High Base is detected

Version 1 may contain placeholder logic.

The purpose is to establish the pipeline.

---

# Opportunity

When an opportunity is produced:

OpportunityType

HIGH_BASE

PatternState

READY

Entry Price

placeholder

Stop Price

placeholder

Confidence

1.0

Quality

5

No execution logic.

No position sizing.

No broker interaction.

---

# Design Principles

Pattern detectors:

- read MarketContext
- never modify MarketContext
- never calculate risk
- never place orders
- never communicate with brokers

Pattern detectors only recognize market structure.

---

# Out of Scope

Do not implement:

- ATR normalization
- SAR confirmation
- Machine learning
- Volume analysis
- Multiple pattern detection
- Trade management

---

# Deliverables

patterns/__init__.py

patterns/detector.py

patterns/high_base_detector.py

Unit tests

Example usage

---

# Acceptance Criteria

HighBaseDetector consumes MarketContext.

HighBaseDetector returns Opportunity or None.

No boolean return values.

No MT4 or MT5 dependencies.

Existing tests continue to pass.

The detector is ready for High Base Rules V1.