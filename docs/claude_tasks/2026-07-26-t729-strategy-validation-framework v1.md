# Task 729: Strategy Validation Framework V1

## Objective

Implement a reusable Strategy Validation Framework that enables manual verification of pattern detectors against TradingView.

The purpose of this task is NOT to optimize any strategy.

The purpose is to make every detector explainable, reviewable, and easy to compare with real market charts.

This framework will become the standard validation workflow for all future pattern detectors (High Base, Flag, Cup & Handle, Trend Pullback, etc.).

---

# Scope

Only implement the validation framework.

Do NOT modify:

- HighBaseDetector logic
- SignalEngine logic
- Pattern detection thresholds
- MarketContext
- Opportunity
- Backtesting

---

# Deliverables

## 1. CLI Arguments

Enhance:

examples/demo_signal_engine.py

Support:

--start YYYY-MM-DD
--end YYYY-MM-DD
--limit N
--review
--signals-only
--export review.csv

Example:

python examples/demo_signal_engine.py \
    --symbol USDJPY \
    --timeframe H1 \
    --start 2025-03-01 \
    --end 2025-03-15 \
    --limit 20 \
    --review \
    --export review.csv

---

## 2. Review Mode

Instead of printing internal rule IDs (HB-001, HB-002, etc.), print descriptive business names.

Example:

==========================================================
Review 7 / 20
==========================================================

Symbol:
USDJPY

Timeframe:
H1

Timestamp:
2025-03-12 08:00

----------------------------------------------------------
TradingView
----------------------------------------------------------

Ticker:
USDJPY

Timeframe:
1H

Go to candle:
2025-03-12 08:00

----------------------------------------------------------
High Base Evaluation
----------------------------------------------------------

Daily Trend Assessment

Expected:
STRONG

Actual:
STRONG

PASS

----------------------------------------------------------

EMA Alignment

EMA20:
149.52

EMA50:
149.30

PASS

----------------------------------------------------------

EMA20 Rising

PASS

----------------------------------------------------------

Impulse Gain

Required:
>= 1.00%

Actual:
0.43%

FAIL

----------------------------------------------------------

Base Width

Required:
<= 0.50%

Actual:
0.31%

PASS

----------------------------------------------------------

Breakout

PASS

----------------------------------------------------------

FINAL RESULT

NO SIGNAL

Reason

Impulse too weak.

---

## 3. CSV Export

Support:

--export review.csv

Generate one row per reviewed context.

Suggested columns:

Timestamp
Symbol
Timeframe

DailyTrend
EMAAlignment
EMASlope
ImpulseGain
BaseWidth
Breakout

Result

FailureReason

The CSV should be easy to open in Excel for manual review.

---

## 4. Human Review Section

At the end of every review block print:

----------------------------------------------------------

Manual TradingView Review

[ ] Looks like a valid High Base

[ ] Not a High Base

[ ] Unsure

Notes:

_________________________________________

This section is intentionally for human review only.

Do NOT export it to CSV.

---

## 5. Design

Avoid putting HighBase-specific formatting directly into demo_signal_engine.py.

Instead introduce a reusable validation/reporting layer.

Suggested structure:

validation/

    __init__.py

    validation_report.py

    validation_formatter.py

The validation layer should be detector-agnostic so future detectors can provide their own explanations without modifying the demo application.

---

## 6. Output Requirements

Default mode:

Keep output concise.

Review mode:

Produce a readable report suitable for comparing with TradingView.

The report should explain:

- Why a signal was generated
- Why a signal was rejected
- Which rule failed
- Actual values
- Expected values

Never print only:

HB-004 FAILED

Instead print meaningful business descriptions.

---

## 7. Constraints

Do not change any detector logic.

Do not optimize thresholds.

Do not change SignalEngine.

Do not change strategy behavior.

This task is strictly about improving explainability and manual validation.

---

## 8. Tests

Add unit tests covering:

- CLI argument parsing
- Date filtering
- Limit filtering
- Signals-only mode
- CSV export
- Review formatting
- Deterministic output
- Empty datasets

Existing tests must continue to pass.

---

## Success Criteria

A user should be able to:

1. Generate a small review dataset (10–20 examples).
2. Open the corresponding candles in TradingView.
3. Compare the detector's reasoning with the chart.
4. Record observations.
5. Use those observations to improve strategy rules in future tasks.

This framework should become the standard validation workflow for every future trading pattern.