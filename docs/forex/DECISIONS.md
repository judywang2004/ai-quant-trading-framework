# AI Quant Trading Framework — Approved Decisions

This file is the authoritative source for user-approved project decisions.

Other documents have narrower roles:

- `docs/forex/FOREX_RESEARCH_TRACK.md` — detailed technical requirements for the Forex Research Track. Do not delete those requirements to resolve a wording conflict.
- `docs/forex/INTEGRATION_PLAN.md` — implementation steps and phase gates.
- `docs/forex/phase0/PHASE0_REVIEW.md` — Phase 0 review record.
- `docs/adr/ADR-003-bar-time-semantics.md` — bar-time semantics.

If a requirements or implementation document conflicts with an approved decision here, this file wins. Raise the conflict and request explicit approval before changing an approved decision.

Update D10 only when the stated status has been verified.

| Decision ID | Decision | Status | Notes |
|---|---|---|---|
| D01 | Preserve Existing MVP | Approved | The one-strategy restriction stays in force on the original MVP track. The Forex Research Track is an explicit exception and must not replace, delete, or modify that strategy. |
| D02 | Forex Research Track | Approved | Donchian is the first research benchmark. Profitability has not been established. |
| D03 | Trading Timeframes | Approved | H1 signals, M5 execution simulation. M15 signals only later. M1 Dukascopy Bid/Ask is raw source data only, resampled to H1 and M5. M1 and tick execution are not approved for the initial implementation. |
| D04 | Trading Frequency | Approved | No fixed 2–5 trades-per-week limit. Measure frequency, net expectancy, and drawdown. M15 only after the H1 baseline. |
| D05 | Risk Management | Approved | 0.25% equity risk cap. Skip trades that the minimum lot would oversize. No martingale or grid. 10% max drawdown is a research objective. |
| D06 | Backtesting Integrity | Approved | No look-ahead. Completed candles only. Execute after the signal is available. Model costs and document intrabar assumptions. |
| D07 | Data | Approved | EURUSD. M1 Dukascopy Bid/Ask is raw source data, resampled to H1 signals and M5 execution bars. UTC timestamps, source timezone metadata kept, configurable trading-day boundary, New York 17:00 rollover and DST tests. |
| D08 | Strategy Validation | Approved | Reproducible backtests, out-of-sample, walk-forward, and cost sensitivity. Report the listed metrics. No profitability claim without evidence. |
| D09 | Development Workflow | Approved | Incremental, testable changes. Regression tests after modifications. Next phase requires approval. |
| D10 | Current Project Status | Approved | Phase 0: implementation and review completed; commits and PR pending. Phase 1: scope approved in principle; implementation awaiting final plan approval. Phase 2: not started. |

## D01 — Preserve Existing MVP

The existing Daily Bias → H1 Pullback → M15 Setup → M5 Trigger strategy remains the primary MVP and must be preserved. A separate Forex Research Track is authorized to develop research infrastructure and benchmark strategies, beginning with Donchian. This does not authorize replacing or deleting existing strategies.

The one-strategy MVP restriction remains in force for the original MVP track. The Forex Research Track is an explicit exception. Do not replace, delete, or modify the original MVP strategy.

## D02 — Forex Research Track

Donchian is the first research benchmark. It does not replace the existing MVP. Its profitability has not been established.

## D03 — Trading Timeframes

H1 is the initial Donchian signal timeframe. M5 is the preferred execution simulation timeframe. M15 may be evaluated for signal generation later. M1 and tick-level execution are outside the initial scope.

M1 Dukascopy Bid/Ask may be used as raw source data. Resample it into H1 signal data and M5 execution simulation data. M1 is not an approved signal or execution timeframe for the initial implementation.

## D04 — Trading Frequency

Do not impose a fixed limit of 2–5 trades per week. Let the strategy generate signals naturally and measure actual trade frequency, net expectancy, and drawdown. We may evaluate M15 signal generation later, but only after establishing the H1 baseline.

## D05 — Risk Management

Maximum initial risk per trade: 0.25% of equity. Skip trades when broker minimum lot size would exceed the permitted risk.

No martingale or grid trading.

Target maximum drawdown: 10%. This is a research objective, not a guaranteed result.

## D06 — Backtesting Integrity

No look-ahead bias. Signals must use completed candles only. Execution must occur after signal availability.

Model spread, commission, slippage, and swap. Document ambiguous intrabar execution assumptions.

## D07 — Data

Initial research symbol: EURUSD. Initial signal and execution-simulation timeframes: H1 and M5.

M1 Dukascopy Bid/Ask may be used as raw source data. Resample it into H1 signal data and M5 execution simulation data. M1 is not an approved signal or execution timeframe for the initial implementation.

Normalize timestamps to UTC. Preserve source timezone metadata. Make trading-day boundaries configurable. Support New York 17:00 rollover and DST tests.

## D08 — Strategy Validation

Use reproducible backtests, out-of-sample testing, walk-forward validation, and cost sensitivity analysis.

Report:

- Net expectancy in R
- Profit factor
- Maximum drawdown
- Weekly and monthly trade frequency
- Annual performance
- Trade ledger and equity curve

Do not claim profitability without evidence.

## D09 — Development Workflow

Preserve existing code and research. Prefer incremental, testable changes. Run regression tests after modifications. Do not proceed to the next phase without approval.

## D10 — Current Project Status

Phase 0: Implementation and review completed; commits and PR pending.

Phase 1: Scope approved in principle; implementation awaiting final plan approval.

Phase 2: Not started.

Update this status only when verified.
