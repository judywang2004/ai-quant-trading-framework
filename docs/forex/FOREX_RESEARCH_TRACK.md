# Forex Research Track: Requirements and Approved Decisions

This is the authoritative list of decisions for the Forex Research Track.
Where `INTEGRATION_PLAN.md` or `GAP_ANALYSIS.md` disagree with this file,
this file wins.

---

## Decision 1: Preserve the existing MVP

The existing Daily Bias → H1 Pullback → M15 Setup → M5 Trigger strategy remains the primary MVP and must be preserved. A separate Forex Research Track is authorized to develop research infrastructure and benchmark strategies, beginning with Donchian. This does not authorize replacing or deleting existing strategies.

(Also recorded verbatim in `CLAUDE.md` and `AGENTS.md`.)

## Decision 2: Trading frequency

Do not impose a fixed limit of 2–5 trades per week. Let the strategy generate signals naturally and measure actual trade frequency, net expectancy, and drawdown. We may evaluate M15 signal generation later, but only after establishing the H1 baseline.

---

## Requirements

1. **Preserve existing work.** The MVP strategy and the High Base research
   (detector, validation, research reports) are kept intact. The track is
   additive.
2. **Initial benchmark:** Donchian Breakout on **H1** signals.
3. **Execution simulation timeframe:** **M5** is preferred.
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
10. **Approval gates:** work proceeds in phases. Phase 1 does not start
    without explicit approval.

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

- **Source:** Dukascopy **M1 Bid and Ask** historical data.
- **Storage:** raw historical data is kept **outside Git**.
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
- **Intrabar ambiguity:** M5 (or M1) OHLC does not reveal the true order of
  stop-loss and take-profit events inside a bar. When both are touched in
  the same bar, assume the **adverse outcome (stop first)**. Fills on gaps
  happen at the bar's open, not the stop price. Every such assumption is
  documented in the report.
- **Model changes** must be backward-compatible, with impact analysis and
  regression tests.

## Phases

| Phase | Scope | Status |
|---|---|---|
| 0 | Correctness and regression tests | Done (`phase0/PHASE0_REVIEW.md`) |
| 1 | Historical data infrastructure and realistic FX backtesting | Awaiting approval |
| 2 | Donchian baseline implementation and validation | Not started |
