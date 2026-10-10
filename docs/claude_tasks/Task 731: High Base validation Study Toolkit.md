ask 731 – High Base Validation Study Toolkit
Build the tooling to support a 50-case manual validation study.
Requirements:
Add a --csv-review <file> option to examples/demo_signal_engine.py.
Export one row per reviewed context.
Include:Timestamp
Symbol
Timeframe
DetectorDecision
DailyTrend
EMAAlignment
ImpulseGain
BaseWidth
Breakout
HumanDecision (blank)
Notes (blank)

Do not change any detector logic.
Do not change thresholds.
Add unit tests for CSV generation.
The output should be directly usable as the "golden dataset" for manual TradingView review.
