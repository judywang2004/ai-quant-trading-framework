# Forex Research Track: Requirements and Approved Decisions

This file contains the detailed technical requirements for the Forex Research Track.

`DECISIONS.md` is the authoritative source for user-approved project decisions. This file does not override it. `INTEGRATION_PLAN.md` contains implementation steps and phase gates and does not override either file. Requirements below are kept; do not delete them to resolve a wording conflict.

---

## Decision 1: Preserve the existing MVP

The existing Daily Bias → H1 Pullback → M15 Setup → M5 Trigger strategy remains the primary MVP and must be preserved. A separate Forex Research Track is authorized to develop research infrastructure and benchmark strategies, beginning with Donchian. This does not authorize replacing or deleting existing strategies.

(Also recorded verbatim in `DECISIONS.md` D01, `CLAUDE.md`, and `AGENTS.md`.)

The one-strategy MVP restriction remains in force for the original MVP track. This research track is an explicit exception. Do not replace, delete, or modify the original MVP strategy.

## Decision 2: Trading frequency

Do not impose a fixed limit of 2–5 trades per week. Let the strategy generate signals naturally and measure actual trade frequency, net expectancy, and drawdown. We may evaluate M15 signal generation later, but only after establishing the H1 baseline.

---

## Requirements

1. **Preserve existing work.** The MVP strategy and the High Base research
   (detector, validation, research reports) are kept intact. The track is
   additive.
2. **Initial benchmark:** Donchian Breakout on **H1** signals.
3. **Execution simulation timeframe:** **M5**. EURUSD M5 Bid/Ask historical data is the preferred initial research dataset. M1 Bid/Ask data is optional and may be resampled to M5 when direct M5 data is unavailable or unsuitable. H1 signal bars are derived from validated M5 data. M1 is not an approved signal or execution timeframe for the initial implementation (D03, D07).
4. **M15 signal generation** may be evaluated later, only after the H1
   baseline is established (Decision 2).
5. **No arbitrary weekly trade-count limit** (Decision 2).
6. **No parameter optimization merely to increase trading frequency.**
7. **Every backtest report must show:**
   - actual trade frequency per **week** and per **month**
   - **net expectancy in R** (after all costs)
   - **maximum drawdown**
8. **Risk per trade is capped at 0.25% of equity.**
9. **Minimum-lot rule:** if the broker's minimum lot size (or lot step)
   would make the trade risk more than the 0.25% cap, **skip the trade**.
   Never round the size up past the cap. Skipped trades are counted and
   reported.
10. **Approval gates:** work proceeds in phases. Phase 1 scope is approved
    in principle. Implementation does not start until the final plan is
    approved. Phase 2 has not started.
11. **Validation workflow (`DECISIONS.md` D11):** Pine visual sanity check →
    Python research framework → MQL5 EA (only after research acceptance) →
    MT5 Strategy Tester with real ticks. Details are in
    [`VALIDATION_WORKFLOW.md`](VALIDATION_WORKFLOW.md).
12. **Pine Strategy Tester results never count as profitability
    evidence.** Research evidence comes from the Python framework only
    (out-of-sample, walk-forward, cost sensitivity).
13. **Differences between TradingView and Python execution assumptions are
    documented** (`VALIDATION_WORKFLOW.md` §4) and kept current when either
    side changes.
14. **No MQL5 EA code before research acceptance.**
15. **Stage timing:** the Pine sanity check may run alongside Phase 1
    infrastructure work. It must be completed before the first Python
    Donchian baseline run (Phase 2.3). Phase 1 implementation still needs
    its own approval.

## Pine visual sanity check requirements (Stage 1)

Full specification: [`VALIDATION_WORKFLOW.md`](VALIDATION_WORKFLOW.md) §2.

- File `pine/forex/donchian_h1_baseline.pine`, TradingView Pine Script v6, EURUSD H1.
- Baseline parameters as approved below: entry channel 20 completed H1 bars, exit channel 10 completed H1 bars, ATR length 14, initial stop 2 × ATR, `LONG_ONLY` / `SHORT_ONLY` / `BOTH`.
- One open position at a time, no pyramiding, no automatic reversal, no fixed weekly trade limit, no martingale or grid.
- Breakout signals are confirmed only after the H1 bar has closed.
- Signal time (signal-bar close) and execution time (next-bar fill) are kept and shown separately.
- The ATR value is captured when the entry signal is confirmed.
- The initial stop is set relative to the actual simulated entry fill price, once. It is not recalculated on later H1 bars. Only the 10-bar exit channel may tighten the stop.
- Risk setting 0.25% (D05) is unchanged until the user approves a revision. Pine sizing is diagnostic only and must not be presented as broker-accurate sizing.
- Pine Strategy Tester results are not profitability evidence.

## Approved Donchian baseline (research benchmark, not optimized)

These are baseline research parameters. They are not optimized and are not
claimed to be profitable.

| Parameter | Value |
|---|---|
| Signal timeframe | H1 |
| Breakout channel | 20 completed bars |
| Exit channel | 10 completed bars (opposite side) |
| Initial stop | 2 × ATR(14) |
| Max equity risk per trade | 0.25% |
| Direction modes | `LONG_ONLY`, `SHORT_ONLY`, `BOTH` |

## Approved data and time conventions

- **Source:** Dukascopy EURUSD **M5 Bid and Ask** historical data is the
  preferred initial research dataset. **M1 Bid and Ask** data is optional
  and may be resampled to M5 when direct M5 data is unavailable or
  unsuitable. H1 signal bars are derived from validated M5 data. M1 is not
  an approved signal or execution timeframe for the initial implementation
  (D03, D07).
- **Storage:** raw historical data is kept **outside Git**. Normalized
  historical data is stored as local **Parquet** (pandas + pyarrow), also
  outside Git (D11).
- **Time:** **UTC internally.**
- **FX trading-day boundary:** configurable. The initial convention is
  **17:00 America/New_York**. Do not assume all MT5 brokers use identical
  daily candle boundaries. The bundled MT4 USDJPY data, for example,
  starts its D1 bars at 18:00 New York in summer
  (`phase0/PHASE0_REVIEW.md` §2).

## Approved simulation principles

- **Closed-candle rule:** a strategy never reads a candle before it has
  fully closed (ADR-003). Execution happens strictly after
  `signal_available_time`.
- **Intrabar ambiguity:** M5 OHLC does not reveal the true order of
  stop-loss and take-profit events inside a bar. The same ambiguity would
  apply to any finer OHLC bar. When both are touched in the same bar,
  assume the **adverse outcome (stop first)**. Fills on gaps happen at
  the bar's open, not the stop price. Every such assumption is documented
  in the report. Initial execution simulation uses M5, not M1.
- **Model changes** must be backward-compatible, with impact analysis and
  regression tests.

## Phases

| Phase | Scope | Status |
|---|---|---|
| 0 | Correctness and regression tests | Implementation and review completed; commits and PR pending (`phase0/PHASE0_REVIEW.md`) |
| 1 | Historical data infrastructure and realistic FX backtesting | Scope approved in principle; implementation awaiting final plan approval |
| 2 | Donchian baseline implementation and validation | Not started |
