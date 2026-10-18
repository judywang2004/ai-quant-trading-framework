# Integration Plan: Forex EA Research

**Status:** Phase 0 implementation and review completed; commits and PR pending. Phase 1 scope approved in principle; implementation awaiting final plan approval. Phase 2 not started.

Authority:

- [`DECISIONS.md`](DECISIONS.md) is the authoritative source for user-approved project decisions.
- [`FOREX_RESEARCH_TRACK.md`](FOREX_RESEARCH_TRACK.md) contains the detailed technical requirements for the Forex Research Track.
- This file contains implementation steps and phase gates.
- [`VALIDATION_WORKFLOW.md`](VALIDATION_WORKFLOW.md) describes the four validation stages (D11): Pine visual sanity check → Python research → MQL5 EA → MT5 real-tick Strategy Tester.

Phase 0 is recorded in [`phase0/PHASE0_REVIEW.md`](phase0/PHASE0_REVIEW.md).

EURUSD M5 Bid/Ask historical data is the preferred initial research dataset. M1 Bid/Ask data is optional and may be resampled to M5 when direct M5 data is unavailable or unsuitable. H1 signal bars are derived from validated M5 data. M1 is not an approved signal or execution timeframe for the initial implementation.

Goal of the first slice:

```
EURUSD M5 Bid+Ask (Dukascopy CSV; optional: M1 Bid+Ask resampled to M5)
   → normalized UTC M5 QuoteBars (+ quality report) → Parquet store
   → H1 signal bars derived from validated M5 (configurable trading-day boundary)
   → Donchian Breakout signals
   → event-driven M5 execution with spread/commission/slippage
   → trade list + equity curve + metrics report
     (weekly/monthly trade frequency, net expectancy in R, max drawdown)
```

---

## 1. Decisions (resolved)

Numbering in this table is local to the plan. User-approved project decisions are D01–D10 in [`DECISIONS.md`](DECISIONS.md).

| # | Decision | Outcome |
|---|---|---|
| D1 | `CLAUDE.md`/`AGENTS.md` say *one strategy only (bullish trend pullback) until validated*. Adding Donchian/FPC changes that. | **Approved.** The one-strategy restriction remains for the original MVP track. The Forex Research Track is an explicit exception and must not replace, delete, or modify that strategy. Recorded in `DECISIONS.md` D01, both instruction files, and `FOREX_RESEARCH_TRACK.md`. |
| D2 | Long-only MVP rule vs. Donchian (symmetric by nature) | **Approved:** direction modes `LONG_ONLY`, `SHORT_ONLY`, `BOTH`. |
| D3 | Donchian baseline rules (research benchmark, not optimized) | **Approved:** signal TF **H1**. Entry: completed-bar close beyond the 20-bar channel of prior completed bars, executed after the bar closes. Initial stop: **2 × ATR(14)**. Exit: opposite **10-bar** channel (only tightens). No take-profit. One position per symbol. Risk **≤ 0.25%** of equity per trade; **skip the trade** if the minimum lot would exceed it. No fixed weekly trade limit (Decision 2). |
| D4 | Data source | **Approved: Dukascopy M5 BID + ASK as the preferred dataset; M1 BID + ASK optional, resampled to M5** when direct M5 is unavailable or unsuitable (revised 2026-10-17, C4). Raw files are stored outside Git, normalized data as Parquet (D11), UTC internally. H1 signals are derived from validated M5. M1 is not an approved signal or execution timeframe. EURUSD 2015-01-01 → 2025-12-31 to start. You download them (Dukascopy web/JForex export); the loader imports them. An automated downloader comes later. |
| D5 | Data location | **Approved:** outside Git, e.g. `/Volumes/ExternalData/market_data/` set via a single config value. Add a `.gitignore` entry for any in-repo fallback path. |
| D6 | Cost defaults (EURUSD, USD account) | *Proposed; confirm at Phase 1 approval.* Commission $3.50/lot/side, slippage 0.2 pip on market and stop fills, swap off in v1 (flagged in the report). Spread comes from data. All configurable; the report runs a sensitivity table at 0× / 1× / 2× slippage. |
| D7 | Where the docs live | `docs/forex/` (this folder) |
| D8 | Execution timeframe | **Approved: M5.** Optional M1 data is resampled to M5 and is not the execution timeframe. Intrabar SL/TP ambiguity resolved adversely (stop first), and gaps fill at the bar open. |
| D9 | FX trading-day boundary | **Approved:** configurable, initially 17:00 America/New_York. Broker boundaries differ (e.g. the bundled MT4 data uses 18:00 NY in summer). |
| D10 | Phasing | **Approved:** Phase 0 implementation and review completed; commits and PR pending. Phase 1 scope approved in principle; implementation awaiting final plan approval. Phase 2 not started. |

## 2. Approach: extend in place, using the empty placeholders

**Recommendation: extend the existing package. No new platform, repo or
top-level framework.**

Why:
- The repo **already reserved the right files** for most of this:
  `backtesting/engine.py`, `backtesting/metrics.py`, `backtesting/report.py`,
  `execution/backtest_executor.py`, `analytics/performance.py`,
  `indicators/atr.py`, `strategies/breakout.py`, `models/position.py`. They
  are all empty. Filling them matches the documented architecture instead of
  inventing a parallel one.
- The reusable pieces (`PositionSizer`, `OrderRequest`, `Signal`, enums,
  `calculate_ema`, detectors, validation) are small, clean and broker-neutral.
- A separate module tree (e.g. `fx_research/`) would duplicate
  Signal/Order/sizing concepts and violate "Avoid duplicate code".

**Isolation rule inside the repo:** the new path is **additive**. It doesn't
change `Candle`, `MarketData`, `DailyTrendAssessment`, `SimulatedExecutor`, the
MVP strategy, `SignalEngine` or any existing test. The existing High Base and
Trend Pullback research continues to work exactly as today.

## 3. Reuse map

| Need | Reuse | New / extend |
|---|---|---|
| Bar model | `Candle` (as the view type indicators consume) | `models/quote_bar.py`: `QuoteBar` with `bid_candle()`, `ask_candle()` and `mid_candle()` |
| Instrument | n/a | `models/instrument.py`: `Instrument` (pip size, contract, quote ccy, digits, lot step) + EURUSD/USDJPY presets |
| Loader | pattern of `data/csv_loader.py` (stdlib csv, typed output) | `data/dukascopy_loader.py`: merge BID+ASK M5 (or optional M1) files into a `QuoteBar` stream, convert to UTC |
| Normalization | n/a | `data/fx_time.py`: `to_utc`, `fx_trading_day` (17:00 NY), `resample(quote_bars, timeframe)` |
| Quality | n/a | `data/quality.py`: `check_quote_bars() -> QualityReport` |
| Indicators | `indicators/ema.py` style | `indicators/donchian.py`, fill `indicators/atr.py` |
| Strategy | `models/signal.py` `Signal`, `SignalType` | fill `strategies/breakout.py`: `DonchianBreakoutStrategy` |
| Positions | n/a | fill `models/position.py`: `Position`. New `risk/position_manager.py` handles duplicate-blocking and the trailing channel stop. |
| Sizing | **`risk/position_sizer.py` as is** | `Instrument.value_per_price_unit_per_lot(price, account_ccy)` supplies its input |
| Orders | **`execution/order_request.py` as is**, `OrderType` | fill `execution/backtest_executor.py`: fill rules against `QuoteBar` (bid/ask, gap, slippage) |
| Costs | n/a | `backtesting/costs.py`: `CostModel` (commission, slippage, swap, spread floor) |
| Engine | n/a | fill `backtesting/engine.py`: `BacktestEngine` event loop (GAP_ANALYSIS §2.7) |
| Results | `models/trade.py` concept | `backtesting/fills.py` or extend in engine: `ClosedTrade` with cost breakdown. The existing `Trade` is left as is. |
| Metrics / report | `validation_formatter` console style | fill `backtesting/metrics.py`, `backtesting/report.py` |
| Entry point | `examples/demo_*.py` + argparse style of `demo_signal_engine.py` | `examples/run_donchian_backtest.py` |

### Two small, justified touches to existing code

Both are listed for explicit approval and are backward-compatible:

1. **`Signal.take_profit: float` → `float | None`.** Donchian has no TP. Field
   order and all existing call sites are unchanged. `SimulatedExecutor` is only
   ever given signals with a TP. *Alternative if you prefer zero edits:* the
   Donchian strategy returns its own `EntrySignal` type. That's slightly more
   duplication.
2. **`requirements.txt`:** declare `pandas` and `yfinance`, which are already
   imported and installed. This is optional and unrelated to the slice. No new
   dependencies are needed for the slice; everything above is stdlib plus the
   existing matplotlib.

### Why Donchian does not subclass `strategies.strategy_base.Strategy`

The base signature `generate_signal(market: MarketData, current_index: int)`
hard-codes the D1/H1/M15/M5 MVP structure. Changing it would ripple through
the MVP strategy. Faking a `MarketData` would be misleading. For v1,
`DonchianBreakoutStrategy.generate_signal(bars: Sequence[Candle]) -> Signal | None`
takes **completed** signal-timeframe bars only, has a `name` property, and keeps
the same rules (no sizing, no execution). Once a second strategy uses the same
shape (Failed Pullback Continuation), generalizing the base class becomes a
justified, separate refactor.

## 4. Implementation steps by approval phase

Each step is: implement → unit test → verify (TradingView or hand calc where
applicable) → commit. Phase 1 implementation starts only after final plan
approval. Phase 2 has not started and needs its own approval.

### Stage 1: Pine visual sanity check (approved, D11; not started)

Runs alongside Phase 1. It doesn't depend on Phase 1 code. It must be done
before step 2.3. The result is the TradingView reference for the spot checks
in 2.1 and 2.2. Running Stage 1 doesn't approve Phase 1. Phase 1 implementation
still needs its own approval.

| Step | Commit | Deliverable | Verification |
|---|---|---|---|
| P.1 | `feat: add Donchian H1 baseline Pine script` | `pine/forex/donchian_h1_baseline.pine` (spec: `VALIDATION_WORKFLOW.md` §2.2) | Loads on EURUSD H1 without errors and refuses other timeframes |
| P.2 | `docs: record Pine visual sanity check` | `docs/forex/pine/PINE_SANITY_CHECK.md` | Checklist in `VALIDATION_WORKFLOW.md` §2.3. **Not profitability evidence.** |

### Phase 0: Correctness and regression tests (implementation and review completed; commits and PR pending)

Closed-candle access in `MarketData`, timeframe-label validation, removal of
the mislabeled USDJPY M5 file, and the `EMATrendStrategy`/`demo_backtest.py`
repairs. See [`phase0/PHASE0_REVIEW.md`](phase0/PHASE0_REVIEW.md) and ADR-003.

### Phase 1: Historical data infrastructure and realistic FX backtesting (scope approved in principle; implementation awaiting final plan approval)

| Step | Commit | Deliverable | Verification |
|---|---|---|---|
| 1.1 | `feat: add QuoteBar and Instrument models` | `models/quote_bar.py`, `models/instrument.py` (pip size, contract, quote ccy, **min lot, lot step**) | Unit tests: bid/ask/mid views, pip math, EURUSD/USDJPY value-per-lot |
| 1.2 | `feat: add Dukascopy bid/ask M5/M1 loader with UTC normalization` | `data/dukascopy_loader.py`, `data/fx_time.py::to_utc` | Fixture CSVs; asserts tz=UTC, bid/ask merge, mismatched-timestamp handling |
| 1.3 | `feat: add quote data quality report` | `data/quality.py` | Fixtures with duplicates, inverted spread, gaps |
| 1.4 | `feat: resample quotes (optional M1 → M5; M5 → H1/D1) with configurable trading-day boundary` | `data/fx_time.py::resample` (default boundary 17:00 America/New_York) | Unit tests incl. DST transition weeks and a non-default boundary; spot-check D1 OHLC vs TradingView/MT5 |
| 1.5 | `feat: add cost model, risk-capped sizing and backtest executor` | `backtesting/costs.py`, `execution/backtest_executor.py`, `models/position.py`, `risk/position_manager.py` | Fixture tests: fill after signal_available_time at ask/bid, gap-through stop, SL+TP in the same M5 bar → stop first, commission math, **0.25% cap, skip when min lot exceeds the cap** |
| 1.6 | `feat: implement event-driven M5 backtest engine` | `backtesting/engine.py` (strategy-agnostic, tested with stub strategies) | No-look-ahead test (perturbing future bars doesn't change past trades); determinism; zero-cost vs cost run differs by exactly the summed costs |
| 1.7 | `feat: add backtest metrics and report` | `backtesting/metrics.py`, `backtesting/report.py` | Metric unit tests on known series, including **weekly/monthly trade frequency, net expectancy in R, max drawdown**, and skipped-trade counts |

### Phase 2: Donchian baseline implementation and validation (not started)

| Step | Commit | Deliverable | Verification |
|---|---|---|---|
| 2.1 | `feat: add Donchian and ATR indicators` | `indicators/donchian.py`, `indicators/atr.py` (Wilder, period 14) | Hand-computed tests + TradingView spot check on 3 dates |
| 2.2 | `feat: implement Donchian breakout baseline` | `strategies/breakout.py`: 20/10 channels, 2 × ATR(14) stop, `LONG_ONLY` / `SHORT_ONLY` / `BOTH` | Tests: signal only on a completed-bar close beyond the prior channel; explainable debug output. The spec defines the initial-stop reference. Proposed: the same as the Pine requirement (actual fill ∓ 2 × the ATR captured on the signal bar, set once), to be confirmed in the Phase 2 plan. |
| 2.3 | `feat: run EURUSD H1 Donchian baseline` | `examples/run_donchian_backtest.py` | **First EURUSD 2015–2025 report**, per mode, with no parameter tuning. **Prerequisite:** Stage 1 (P.2) recorded. |

**The baseline is done when** one command produces, for EURUSD 2015–2025:
a data-quality summary, trade list CSV, equity curve CSV, and a metrics table.
The metrics show weekly/monthly trade frequency, net expectancy in R, max
drawdown, gross vs. net with cost breakdown, a per-year table, slippage
sensitivity and skipped-trade counts. Everything is reproducible from the
config printed in the report header. No weekly trade-count limit is imposed
(Decision 2).

### Later work (each needs its own approval)

| Item | Content |
|---|---|
| L1 | USDJPY: data import, JPY → USD P&L conversion, same report |
| L2 | Stage 4 (D11): MT5 Strategy Tester, "Every tick based on real ticks", on the L7 EA. Trade-by-trade comparison with the Python ledger on a shared 3–6 month window. Runs after L7, not before. |
| L3 | Swap model from broker table; spread floor calibrated from an MT5 export that includes `MqlRates.spread` (after `mt5/ExportHistory.mq5` is compiled and verified) |
| L4 | M15 signal generation, only after the H1 baseline is established (Decision 2) |
| L5 | Failed Pullback Continuation: written rule spec (rule IDs) → detector via existing `PatternDetector` → explainer → `SignalEngine` detection review → Opportunity→Signal bridge → same engine |
| L6 | Robustness: walk-forward, parameter stability, Monte Carlo of trade order. Never tuning just to raise trade frequency. Ends with the user's **research acceptance** decision (D11 Stage 2 gate). |
| L7 | Stage 3 (D11): MQL5 EA port, only for a strategy the user has accepted after L6. No EA code before that. |

## 5. Existing issues found during inspection

All three were **fixed in Phase 0** (`phase0/PHASE0_REVIEW.md`):

1. Look-ahead in `MarketData` multi-timeframe access.
2. `data/raw/USDJPY_M5.csv` contained M15 bars (removed; loader now validates).
3. `EMATrendStrategy` could not be instantiated; `examples/demo_backtest.py`
   was broken.

## 6. Risks

| Risk | Mitigation |
|---|---|
| Dukascopy spreads tighter than your broker's | Spread floor/markup in `CostModel`; calibrate from an MT5 export (L3) |
| M5 OHLC hides intrabar order of SL/TP | Adverse (stop-first) assumption, documented in every report |
| Pure-Python speed (~740k M5 bars / 10 yrs) | Stream per year; `__slots__` dataclasses; measure before optimizing |
| DST/day-boundary mistakes shift D1/H4 bars | Configurable boundary; dedicated tests on DST weeks; TradingView spot checks |
| Overfitting Donchian parameters | Fixed baseline (20/10/2 × ATR(14)); no tuning before L6, and never just to raise frequency |
| Minimum lot exceeds the 0.25% cap on small accounts | Trade is skipped and counted, never rounded up |
| Pine Strategy Tester results read as evidence | Labeled "visual sanity check, not evidence" wherever recorded. Only Python results count (D08, D11). |
| Pine and Python trade lists differ | Expected. The causes are listed in `VALIDATION_WORKFLOW.md` §4. Stage 1 checks rule logic, not P&L. |
| Scope creep vs. MVP | Decision 1 (CLAUDE.md / AGENTS.md); the track stays additive |

---

**Next action:** final plan approval for Phase 1 implementation, including the D6 cost defaults and the Parquet storage change (`phase1/PHASE1_PLAN.md` §7). Do not start Phase 1 implementation before that approval. Stage 1 (Pine) can start once you approve writing the script.
