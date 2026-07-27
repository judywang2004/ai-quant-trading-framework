# Task 730: Research Report Framework V1

## Objective

Upgrade the Validation Framework into a Research Report Framework.

The goal is no longer simply determining whether a signal exists.

The goal is to make every trading decision fully explainable, reproducible, and easy to verify against TradingView.

The report should answer one question:

> Why did the system make this decision?

Every PASS and FAIL should be backed by raw values, thresholds, and calculations.

This framework will become the standard debugging and research tool for every future detector.

---

# Scope

Do NOT modify:

- detector logic
- SignalEngine
- MarketContext
- Opportunity
- thresholds
- strategy behavior

This task is presentation and explainability only.

---

# Research Mode

Add

--research

to

examples/demo_signal_engine.py

Research mode should produce a much more detailed report than Validation mode.

Review mode remains concise.

Research mode is intended for investigating only a few examples.

---

# Daily Trend Section

Instead of

Daily Trend Assessment

Expected:
STRONG

Actual:
STRONG

print something similar to:

------------------------------------------------------------

Daily Trend Assessment

Daily Candle Used

2026-03-16

Bias

BULLISH

Strength

STRONG

EMA20

159.24618

EMA50

159.20103

Alignment Rule

EMA20 > EMA50

PASS

EMA20 Slope

0.0034%

Threshold

> 0.0000%

PASS

EMA Separation

0.028%

Threshold

>= 0.0000%

PASS

Final Classification

BULLISH STRONG

------------------------------------------------------------

If the assessment is NEUTRAL, clearly explain why.

For example

Final Classification

NEUTRAL

Reason

EMA20 below EMA50.

or

EMA20 falling.

---

# Pattern Rules

For every High Base rule print

Decision

PASS / FAIL

Threshold

Raw Value

Formula (optional if short)

Example

------------------------------------------------------------

Impulse Gain

Decision

FAIL

Formula

(high - low) / low

Threshold

>= 1.00%

Actual

0.11%

------------------------------------------------------------

Base Width

Decision

PASS

Formula

(high - low) / low

Threshold

<= 1.00%

Actual

0.34%

------------------------------------------------------------

Breakout

Decision

FAIL

Required

Close > 159.45300

Actual

Close = 159.36700

------------------------------------------------------------

---

# Traceability

The report must identify every candle used.

Example

Daily Candle

2026-03-16

H1 Candle

2026-03-17 04:00

This makes TradingView replay verification much easier.

---

# Dataset Information

At the beginning of the report print

Dataset

First Context

...

Last Context

...

Contexts Available

...

Requested Range

...

Contexts Selected

...

This prevents confusion when filtering dates.

---

# Research Summary

After all reviews print

================================================

Research Summary

================================================

Contexts Reviewed

20

Signals

0

Rule Failure Counts

EMA Alignment

18

EMA20 Rising

6

Impulse Gain

20

Base Width

0

Breakout

12

Most Common Failure

Impulse Gain

20 / 20

This allows researchers to quickly identify the bottleneck.

---

# Detector Independence

The framework must remain detector-agnostic.

HighBase-specific knowledge should remain inside the explainer layer.

The formatter should only consume generic RuleCheck and ContextReview objects.

Future detectors should plug into the framework without modifying the formatter.

---

# Output Modes

Default

Current concise output.

Review

Current human-readable validation report.

Research

Detailed engineering report with all intermediate values.

---

# Tests

Add tests covering

- research mode formatting
- dataset summary
- rule failure aggregation
- traceability section
- deterministic output
- detector independence
- empty datasets

Existing tests must continue to pass.

---

# Success Criteria

A researcher should be able to:

1. Open TradingView Replay.
2. Navigate to the exact candle.
3. Compare every calculation with TradingView.
4. Understand every PASS and FAIL.
5. Identify which rules are overly strict.
6. Improve detector rules using evidence rather than intuition.

This framework should become the standard research workflow for all future pattern detectors.