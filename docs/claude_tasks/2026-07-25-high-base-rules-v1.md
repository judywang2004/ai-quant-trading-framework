# Objective

Implement the first production trading pattern of the AI Quant Trading Framework.

This task implements High Base Rules V1 according to the documented specification.

Every implemented rule must be traceable to a documented rule ID.

---

# Background

The Pattern Framework is complete.

HighBaseDetector currently contains only placeholder logic.

This task replaces placeholder logic with deterministic rule-based detection.

---

# Rule HB-001

Daily Trend must be STRONG.

Implementation

Reject any MarketContext where:

daily_assessment.strength != STRONG

---

# Rule HB-002

EMA Alignment

Require

EMA20 > EMA50

Reject otherwise.

---

# Rule HB-003

EMA20 Slope

Version 1

EMA20 must be rising.

A simple implementation is acceptable.

Future versions may replace this with regression or normalized slope.

---

# Rule HB-004

Impulse Leg

The consolidation must be preceded by a meaningful bullish move.

Version 1

A simple price-expansion heuristic is acceptable.

Document the chosen heuristic.

---

# Rule HB-005

High Base

Detect a relatively tight consolidation near recent highs.

Version 1 implementation may use:

- configurable lookback
- configurable maximum range

The detector should expose configuration values as constants or parameters rather than embedding magic numbers.

---

# Rule HB-006

Breakout

Current candle closes above the consolidation high.

Version 1

Close-based confirmation only.

No intrabar detection.

---

# Rule HB-007

Opportunity

If every rule passes:

Return

OpportunityType.HIGH_BASE

PatternState.READY

entry_price = breakout price

stop_price = base low

confidence = 1.0

quality = 5

Otherwise

Return None

---

# Design Principles

The detector must:

- consume only MarketContext
- never modify MarketContext
- never calculate indicators
- never calculate position size
- never communicate with brokers

---

# Configuration

Avoid magic numbers.

Expose configurable values such as:

BASE_LOOKBACK

MIN_BASE_CANDLES

MAX_BASE_RANGE

BREAKOUT_BUFFER

as named constants.

Future versions will move these into configuration.

---

# Deliverables

Updated HighBaseDetector

Unit tests

Rule documentation comments

---

# Acceptance Criteria

Every rule HB-001 through HB-007 has:

- implementation
- corresponding unit test

Detector returns only:

Opportunity

or

None

Existing test suite passes.

No MT4/MT5 dependencies.

No broker-specific code.

---

# Definition of Done

- [ ] HB-001 implemented
- [ ] HB-002 implemented
- [ ] HB-003 implemented
- [ ] HB-004 implemented
- [ ] HB-005 implemented
- [ ] HB-006 implemented
- [ ] HB-007 implemented
- [ ] Tests added
- [ ] Existing tests passtouch 