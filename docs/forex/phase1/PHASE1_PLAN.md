# Phase 1 Implementation Plan: Historical Data, FX Execution Simulation, Risk Sizing, Analytics

**Status:** PROPOSED. Awaiting confirmation. No Phase 1 code has been written.

Governing records: `DECISIONS.md` (binding), `FOREX_RESEARCH_TRACK.md`,
`INTEGRATION_PLAN.md`, `VALIDATION_WORKFLOW.md`, ADR-003.

Phase 1 is part of Stage 2 (Python research framework) of the D11 validation
workflow. It doesn't depend on Stage 1 (Pine).

**Out of scope:** the Donchian strategy and the ATR/Donchian indicators
(Phase 2), any change to the MVP strategy or the High Base research, M1 or
tick execution, M15 signals, swap modeling, walk-forward runs, USDJPY, and
live/MT5 execution.

---

## 1. Conflicts with the registry (need your explicit confirmation)

| # | Registry text | Phase 1 instruction | Proposed handling |
|---|---|---|---|
| C1 | D06: "Model spread, commission, slippage, **and swap**." | "First version may use zero swap; reports must state 'Swap not modeled.'" | Swap = 0 in Phase 1. Every report prints the exact line `Swap not modeled.` and never calls results "fully realistic net performance". **Please confirm, and amend D06 if you want the registry to reflect this deferral.** |
| C2 | D08: out-of-sample and walk-forward validation | Phase 1 = infrastructure | Phase 1 supports **date-window runs** (`--start/--end`) and per-year tables, so in-sample/out-of-sample splits are possible. A walk-forward **runner** is deferred to Phase 2 or later. |
| C3 | ADR-003: execution "strictly after `signal_available_time`" | M5 execution | An H1 signal available at 13:00:00 fills at the **open of the M5 bar starting 13:00**. That's the first price after the H1 close, but its *bar timestamp* equals `signal_available_time`. The engine enforces `fill_bar.open_time >= signal_available_time`, never a bar that opened earlier. **Please confirm this reading.** An optional `execution_delay_bars` (default 0) is available for stricter tests. |
| C4 | D03/D07 summary rows: "M1 Dukascopy Bid/Ask is raw source data, resampled to H1 signals and M5 execution bars." | D11: "Prefer M5 data for Python execution simulation. M1 is optional, not mandatory." | The detailed D03/D07 text already says M1 "may be used", so M1-as-source stays supported. Proposed addition: the loader also accepts **Dukascopy M5 bid/ask exports directly** (H1 is then resampled from M5). M1 import stays optional. M1 is never an execution or signal timeframe. **Resolved 2026-10-17:** approved. D03/D07 revised: M5 Bid/Ask preferred, M1 optional (resampled to M5), H1 derived from validated M5. |

D05's 10% maximum-drawdown *research objective* is reported as a pass/fail
line against the measured max drawdown. It's informational and never used
to change parameters.

## 2. Design summary

```
Dukascopy M5 BID+ASK csv (preferred)        Dukascopy M1 BID+ASK csv (optional)
              │                                          │
              │                       resample to M5 (bid & ask independently)
              └──────────────────┬───────────────────────┘
                                 ▼
                     M5 QuoteBars (UTC) ─► quality report
                                 │
                         validated M5 QuoteBars ─► resample (bid & ask independently) ─► H1 QuoteBars
                                 │                                                          │
                                 ▼                                                          ▼
                     quote store (Parquet + manifest JSON, outside Git)
                                 │
   test/stub strategy (Phase 1) ─► BacktestEngine (M5 event loop, H1 released at close)
                                 │  risk sizing (0.25% cap, min-lot skip)
                                 │  BacktestExecutor (bid/ask fills, slippage, commission)
                                 ▼
          ledger CSV · equity CSV · report (metrics, sensitivity 0.2/0.5/1.0 pip)
```

Principles:

- **Additive only.** New modules, plus filling **existing empty placeholder
  files** (`backtesting/engine.py`, `metrics.py`, `report.py`,
  `execution/backtest_executor.py`, `models/position.py`, `config/settings.py`).
  All of these are 0 bytes today and nothing imports them.
- **Dependencies: pandas + pyarrow** for Parquet storage (D11), declared in
  `requirements.txt` in commit 1.6. pandas is used at the storage boundary
  (write/read Parquet). The engine still consumes `QuoteBar` objects, so its
  design is unchanged. Everything else is stdlib (`csv`, `json`, `zoneinfo`,
  `hashlib`) plus matplotlib (already declared) for an optional equity PNG.
- **No changes to existing models.** `Candle`, `Signal`, `Trade`,
  `MarketData`, `PositionSizer` and `SimulatedExecutor` are untouched. The
  earlier proposal to make `Signal.take_profit` optional is **dropped**:
  Phase 1 uses its own `EntryIntent`, so it isn't needed.
- Strategy-facing data obeys ADR-003. The engine releases an H1 bar only
  when the M5 clock reaches its close.

## 3. File-level plan

### models/
| File | Status | Content |
|---|---|---|
| `models/quote_bar.py` | new | `QuoteBar` (frozen, slots): `symbol, timeframe, timestamp` (tz-aware **UTC**, bar open), `bid_open/high/low/close`, `ask_open/high/low/close`, `volume`, `component_count` (source bars aggregated). Constructor rejects naive or non-UTC timestamps. Views `bid_candle()`, `ask_candle()`, `mid_candle()` return the existing `Candle`. |
| `models/instrument.py` | new | `Instrument`: symbol, base/quote ccy, contract_size, pip_size, digits, **min_lot, lot_step, max_lot**. `value_per_price_unit_per_lot(account_ccy)` supports quote ccy = account ccy (EURUSD/USD) and raises `NotImplementedError` otherwise (USDJPY is later work, L1). Preset `EURUSD` (100,000; 0.0001; 5 digits; min 0.01; step 0.01). |
| `models/position.py` | fill placeholder | `Position` (open position state: id, side, lots, entry fill, initial stop, current stop, optional TP, initial risk amount, signal_available_time, entry costs, MAE/MFE tracking). |

### data/
| File | Status | Content |
|---|---|---|
| `data/fx_time.py` | new | `to_utc(naive, source_tz)` (zoneinfo, explicit handling of DST-ambiguous and nonexistent times). `TradingDayBoundary(hour=17, minute=0, tz="America/New_York")`, configurable, with `trading_day_start(t_utc)`. Bucket helpers: M5/H1 floor in UTC; D1 by boundary. |
| `data/dukascopy_loader.py` | new | Parse Dukascopy M5 CSV exports (preferred) and optional M1 exports. The input timeframe is declared and checked against the timestamp spacing (header detected: `Gmt time` / `Time (UTC)` variants, `dd.mm.yyyy HH:MM:SS.fff`). Unknown formats fail loudly. Merge BID + ASK by timestamp into M5 (or M1) `QuoteBar`s. Unmatched timestamps and Dukascopy flat filler bars (O=H=L=C, volume 0) are **dropped and counted**, never silently. Returns bars + `SourceMetadata`. |
| `data/source_metadata.py` | new | `SourceMetadata`/manifest: provider, symbol, price sides, source timezone, file names, SHA-256, row counts, dropped counts, first/last UTC timestamp, import time, boundary config. Serialized as JSON next to the stored data (registry D07: preserve source timezone metadata). |
| `data/resample.py` | new | `resample(bars, "M5" | "H1" | "D1", boundary)`: optional M1 → M5, and validated M5 → H1/D1. **Bid and ask aggregated independently**: open = first, high = max, low = min, close = last per side; the bar timestamp is the bucket open (UTC); `component_count` is recorded. Never forward-fills missing bars. Rejects M1 as an output timeframe for research use (registry D03). |
| `data/quality.py` | new | `QualityReport` over M1/M5/H1 quote bars: duplicates, non-monotonic timestamps, ask < bid, per-side OHLC inconsistency, spread stats (pips: median, p95, p99, max), **gaps** (expected weekend vs. unexpected intra-session, with a list), **session boundaries** (weekly open/close observed in New York local time), **DST checks** (US/EU transition weeks: the weekly open must stay at the configured NY boundary while its UTC time shifts by 1h). Plain-text summary for reports. |
| `data/quote_store.py` | new | Write/read normalized M5 and H1 quote bars as **per-year Parquet files** (pandas + pyarrow; UTC `timestamp[ns, tz=UTC]` column, explicit schema) plus `manifest.json` under an external root. Streaming reader (year by year). Refuses to write inside the Git working tree. |
| `config/settings.py` | fill placeholder | `market_data_root()` from env var `AQTF_MARKET_DATA_ROOT`, with a clear error if it's unset. No defaults inside the repo. |

### risk/
| File | Status | Content |
|---|---|---|
| `risk/lot_sizing.py` | new | `size_trade(equity, entry_estimate, stop, instrument, risk_cap=0.0025, slippage_pips)` → `LotDecision(lots or None, skip_reason, intended_risk)`. Reuses the existing `PositionSizer` for raw lots. The risk distance **includes the slippage assumption**. Lots are rounded **down** to `lot_step`. If the result is below `min_lot`, the trade is **skipped** (`MIN_LOT_EXCEEDS_RISK_CAP`), never rounded up. Equity is current equity (fixed-fractional): no loss-recovery scaling and no martingale. |
| `risk/position_manager.py` | new | One open position per symbol; additional entries are rejected (no grid, no pyramiding). Stop updates are accepted only if they **tighten**. |

### execution/
| File | Status | Content |
|---|---|---|
| `execution/backtest_executor.py` | fill placeholder | `BacktestExecutor` fill model on M5 `QuoteBar`s. **Market entry:** BUY at `ask_open + slip`, SELL at `bid_open − slip`. **Long stop:** triggered by `bid_low <= stop`; fill at `stop − slip`, or at `bid_open − slip` if the bar gapped through. **Short stop:** `ask_high >= stop`, mirrored. **Take-profit** (optional): limit fill at TP with no slippage. **SL and TP in the same bar → SL** (adverse; documented). Exits on the entry bar are evaluated from the entry fill onward using that bar's OHLC (conservative: SL wins). Commission per lot per side at entry and exit. |

### backtesting/
| File | Status | Content |
|---|---|---|
| `backtesting/costs.py` | new | `CostModel(commission_per_lot_per_side=3.50, slippage_pips=0.2, swap_modeled=False)`, plus `SLIPPAGE_SCENARIOS = (0.2, 0.5, 1.0)`. Spread is not a parameter: it comes from bid/ask data. |
| `backtesting/strategy_protocol.py` | new | Phase 1 interface the engine calls (Donchian implements it in Phase 2): `on_signal_bar_closed(closed_h1_bars, position) -> EntryIntent | StopUpdate | None`. Strategies never size, fill or hold positions (CLAUDE.md). |
| `backtesting/ledger.py` | new | `LedgerEntry`: signal_available_time, entry/exit time and price, side, lots, intended and realized initial risk, gross P&L, spread cost (vs. mid), slippage cost, commission, swap (=0, flagged), net P&L, R multiple, MAE/MFE (R), exit reason. Plus `SkippedTrade` records. CSV writer. |
| `backtesting/engine.py` | fill placeholder | `BacktestEngine`: deterministic M5 event loop. Per M5 bar: (1) fill orders queued for this bar; (2) evaluate stops/TP; (3) mark-to-market at close (bid for longs, ask for shorts); (4) if this bar's close completes an H1 bar, release it and call the strategy; (5) size and queue resulting orders for the next M5 bar. Streams data year by year. Asserts that no H1 bar is released before its close and no fill happens on a bar that opened before `signal_available_time`. |
| `backtesting/metrics.py` | fill placeholder | From ledger + equity curve: net/gross P&L, **profit factor**, **net expectancy in R**, win rate, avg win/loss (R), **max drawdown** (abs, %, start/trough/recovery dates) vs. the 10% objective, **trade frequency per ISO week and per calendar month** (mean, median, min, max, weeks with zero trades), **annual performance** table, **skipped-trade count** by reason, costs as % of gross, exposure, longest losing streak. |
| `backtesting/report.py` | fill placeholder | Text/Markdown report: header (data manifest summary, date window, config, cost model), the data-quality summary, metrics, annual table, **slippage sensitivity table (0.2 / 0.5 / 1.0 pip)**, assumptions section (intrabar SL-first, gap fills, fill timing per C3), and the verbatim line **`Swap not modeled.`** Writes the ledger CSV, equity CSV and optional PNG. |
| `backtesting/sensitivity.py` | new | Re-runs the same deterministic backtest per slippage scenario and returns a comparison table. |

### examples/ (CLI entry points)
| File | Content |
|---|---|
| `examples/import_dukascopy.py` | `--bid FILE --ask FILE --symbol EURUSD --source-tz UTC` → quality report + M5/H1 store + manifest under `AQTF_MARKET_DATA_ROOT`. |
| `examples/run_engine_smoke.py` | Runs the engine on stored EURUSD data with a **scripted test strategy** (fixed, documented entries, not a trading idea) to prove the end-to-end path and produce a sample report. Clearly labeled "infrastructure check, not a strategy result". |

### tests/ (new)
`test_quote_bar.py`, `test_instrument.py`, `test_fx_time.py`,
`test_dukascopy_loader.py`, `test_resample.py`, `test_quality.py`,
`test_quote_store.py`, `test_lot_sizing.py`, `test_position_manager.py`,
`test_backtest_executor.py`, `test_backtest_engine.py`,
`test_backtest_metrics.py`, `test_backtest_report.py`. Fixtures are small
synthetic CSVs under `tests/fixtures/dukascopy/` (a few KB, committed).

## 4. Proposed commit breakdown (each passes the full suite)

| # | Commit | Files |
|---|---|---|
| 1.1 | `feat: add QuoteBar and Instrument models` | `models/quote_bar.py`, `models/instrument.py` + tests |
| 1.2 | `feat: add UTC conversion and configurable FX trading-day boundary` | `data/fx_time.py` + tests |
| 1.3 | `feat: import Dukascopy M5/M1 bid/ask with source metadata` | `data/dukascopy_loader.py`, `data/source_metadata.py`, fixtures + tests |
| 1.4 | `feat: resample quotes to M5/H1/D1 with independent bid/ask aggregation` | `data/resample.py` + tests |
| 1.5 | `feat: add quote data quality report` | `data/quality.py` + tests |
| 1.6 | `feat: add external Parquet quote store and Dukascopy import CLI` | `data/quote_store.py`, `config/settings.py`, `examples/import_dukascopy.py`, `requirements.txt` (pandas, pyarrow) + tests |
| 1.7 | `feat: add cost model and risk-capped lot sizing` | `backtesting/costs.py`, `risk/lot_sizing.py` + tests |
| 1.8 | `feat: add position manager and bid/ask backtest executor` | `models/position.py`, `risk/position_manager.py`, `execution/backtest_executor.py`, `backtesting/ledger.py` + tests |
| 1.9 | `feat: implement event-driven M5 backtest engine` | `backtesting/strategy_protocol.py`, `backtesting/engine.py` + tests |
| 1.10 | `feat: add backtest metrics, report and slippage sensitivity` | `backtesting/metrics.py`, `backtesting/report.py`, `backtesting/sensitivity.py`, `examples/run_engine_smoke.py` + tests |
| 1.11 | `docs: record Phase 1 review` | `docs/forex/phase1/PHASE1_REVIEW.md` (results, real-data import summary if data is available, open risks) |

## 5. Acceptance tests

**Data**
- A1: Dukascopy M5 BID+ASK fixture → M5 QuoteBars with tz-aware UTC timestamps (and the same for an optional M1 fixture). A bar missing on one side is dropped and counted. Flat filler bars are dropped and counted. An unknown header raises.
- A2: Naive source times in a DST zone convert correctly, including ambiguous (fall-back) and nonexistent (spring-forward) local times.
- A3: Resample: hand-computed H1 bars from an M5 fixture (and M5 bars from an optional M1 fixture) where bid and ask extremes occur in **different** source bars. The test proves independent aggregation (ask_high ≠ bid_high + constant spread). `component_count` is correct. No forward-fill.
- A4: D1 with the 17:00 NY boundary: a Sunday-evening open belongs to Monday's trading day, and the boundary's UTC hour shifts by 1 across **both** US DST transitions. A non-default boundary (e.g. 00:00 UTC) yields different bars.
- A5: Quality: duplicates, out-of-order, ask < bid, OHLC violations, an unexpected mid-session gap, an expected weekend gap and a DST week are each detected and classified on fixtures.
- A6: Store round-trip: write → read of Parquet reproduces bars (including UTC tz and float prices) and manifest exactly. Writing inside the repo is refused. Source timezone and file hashes are preserved.

**Risk**
- A7: EURUSD, $10,000 equity, 20-pip stop + 0.2-pip slippage → lots round **down** to 0.01 steps and risk ≤ $25 (0.25%).
- A8: Small equity / wide stop where 0.01 lot exceeds 0.25% → trade **skipped** with reason, and the skip is counted in the report.
- A9: A second entry while a position is open is rejected (no grid or pyramiding). A loosening stop update is rejected. The size after a loss is never larger than fixed-fractional on current equity (no martingale).

**Execution**
- A10: BUY fills at next M5 `ask_open + 0.2 pip`; SELL at `bid_open − 0.2 pip`.
- A11: A long stop is triggered on **bid** low, a short stop on **ask** high. Spread alone can stop out a short.
- A12: A gap through the stop fills at the bar open (worse than the stop).
- A13: SL and TP touched in the same M5 bar → SL.
- A14: Commission = $3.50 × lots × 2 per round trip. Ledger buckets (spread, slippage, commission) sum exactly to gross − net.

**Engine integrity**
- A15: Look-ahead perturbation: changing any bar **after** time T leaves every ledger entry with entry before T unchanged.
- A16: No H1 bar reaches the strategy before its close. No fill is on an M5 bar opening before `signal_available_time` (per C3).
- A17: Determinism: two runs produce byte-identical ledger and equity CSVs.
- A18: Weekend: a Friday-close signal fills at the Sunday open price.

**Analytics**
- A19: Metrics on a hand-built ledger: profit factor, net expectancy in R, max drawdown (abs, %, dates), weekly/monthly frequency including zero-trade weeks, and an annual table all match hand-computed values.
- A20: The report contains the verbatim line `Swap not modeled.` and does not contain "fully realistic". Gross vs. net and skipped counts are present. The sensitivity table has rows for 0.2, 0.5 and 1.0 pip, and net P&L is non-increasing as slippage rises.

**Regression**
- A21: All existing tests (205) pass unchanged after every commit. All existing demos still run. `git diff` shows no modifications to MVP, High Base, validation or existing model files.

**Real data (conditional)**
- A22: If you provide Dukascopy EURUSD M5 BID+ASK files (or optional M1), import 2015–2025, and record the quality report and manifest summary in `PHASE1_REVIEW.md`. The smoke run produces a full report. No strategy conclusions are drawn.

## 6. Compatibility impact

- **Existing behavior:** none changed. No existing module is modified. Only
  empty placeholder files are filled, and nothing imports them today.
- **Public interfaces:** unchanged. `Signal`, `Candle`, `Trade`,
  `MarketData`, `PositionSizer` and `SimulatedExecutor` are untouched.
  `PositionSizer` is reused, not altered.
- **Dependencies:** pandas and pyarrow added (D11). pandas is already installed but undeclared. pyarrow is new.
- **Repository size:** only small synthetic fixtures are committed. Real
  market data lives under `AQTF_MARKET_DATA_ROOT` outside Git.
- **Performance:** ~740k M5 bars per 10 EURUSD years, streamed per year.
  Expected minutes per run in pure Python; to be measured and reported, not
  optimized.

## 7. Open items needing your input

1. Confirm conflicts **C1–C3** (§1). C4 is resolved.
2. Choose the data location (proposed: `/Volumes/ExternalData/market_data/`) for `AQTF_MARKET_DATA_ROOT`.
3. Real-data acceptance (A22) needs the Dukascopy EURUSD **M5 BID and ASK** CSV exports for 2015–2025 (M1 optional). Without them, Phase 1 completes on fixtures only.
4. Git: push and PR are on hold, as you instructed.
5. Parquet storage replaces the earlier `CSV.gz` proposal (D11). Adding `pandas` and `pyarrow` is **approved** (2026-10-17). They are declared explicitly in `requirements.txt` in commit 1.6 with compatible-release constraints (e.g. `pandas~=3.0`, matching the installed 3.0.3, and `pyarrow` constrained the same way to the version installed then). Nothing is installed or declared before Phase 1 approval.
