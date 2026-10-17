# Current Architecture

Snapshot of the repository as of 2026-10-16, branch `feature/trading-memory-v1`
(HEAD `2f07cba`, clean working tree). Written as input to the Forex EA research
work (EURUSD/USDJPY Donchian Breakout and Failed Pullback Continuation). No code
was changed to produce this document.

---

## 1. Languages, tooling, dependencies

| Item | State |
|---|---|
| Language | Python 3.11.6 (`.venv`), `requires-python >= 3.10` |
| Packaging | `pyproject.toml`, setuptools, flat layout, explicit package list, `pip install -e .` |
| Tests | `pytest` / `unittest`, **170 tests, all passing in 0.1 s** |
| Runtime deps (`requirements.txt`) | numpy, scipy, scikit-learn, lightgbm, xgboost, matplotlib (+ transitive) |
| Installed but **not declared** | `pandas 3.0.3`, `yfinance 1.5.1` (`data/yfinance_loader.py` imports yfinance) |
| Not present | pandas-based pipelines, Parquet/pyarrow, DuckDB, any broker SDK (`MetaTrader5` package) |
| Other languages | MQL5 (`mt5/ExportHistory.mq5`), Pine (`pine/trend_pullback_strategy.pine` is empty) |
| CI | `.github/workflows/` exists but is empty |

The core code is written in plain stdlib Python: lists of frozen dataclasses,
`csv`, `datetime` and `enum`. It doesn't use pandas or numpy anywhere.

## 2. Governing documents

| File | What it says that matters here |
|---|---|
| `CLAUDE.md` / `AGENTS.md` (identical) | MarketData → Strategy → RiskManager → PositionManager → Executor. Strategies never execute or manage positions. **MVP is one strategy (bullish multi-timeframe trend pullback); "Do not introduce additional strategy ideas until the MVP has been validated."** One rule at a time, unit tested, verified against TradingView, then committed. |
| `VISION.md` | Research-first. "Replay outcome is the truth." Phase 2 mentions DuckDB. Guiding question: *will this help us discover profitable edge faster?* |
| `docs/project_structure.md` | Intended layering: Domain (models, strategies, risk, indicators) ← Application (backtesting, analytics, dashboard) ← Infrastructure (execution, mt5, pine). |
| `docs/milestones/MILESTONE-001` | Claims "ADR-001 Bar-Driven Engine" and "Ready for Backtesting". **The ADR-001 file does not exist** in `docs/adr/`. Only ADR-002 does. |
| `docs/roadmap.md` | V0.5 H1 Pullback → V0.9 MT5 Executor → V1.0 AI filter. |

The one-strategy restriction applies to the original MVP track. The separately approved Forex Research Track is an explicit exception, governed by docs/forex/DECISIONS.md.

## 3. Module inventory

Legend: ✅ working and tested · 🟡 working with caveats · ⬜ empty placeholder file

### models/ (domain objects)
| File | State | Notes |
|---|---|---|
| `candle.py` | ✅ | `Candle(symbol, timeframe, timestamp, open, high, low, close, volume)`, frozen. **Single price series. No bid/ask or spread.** |
| `signal.py` | ✅ | `Signal(symbol, timeframe, timestamp, signal_type, strategy_name, entry, stop_loss, take_profit, confidence)`. `take_profit` is required. |
| `order.py`, `trade.py` | 🟡 | Minimal. `Trade` has a single `profit` float with no cost breakdown. |
| `enums.py` | ✅ | `SignalType`, `OrderStatus`, `OrderType` (MARKET/LIMIT/STOP), `TradeStatus` |
| `market_bias.py`, `trend_assessment.py` | ✅ | Used by DailyTrendAssessment |
| `position.py`, `portfolio.py` | ⬜ | |

### core/
| File | State | Notes |
|---|---|---|
| `market_data.py` | 🟡 | `MarketData(daily, h1, m15, m5)`, **hard-wired to 4 timeframes**. Linear-scan lookups (`*_at`, `*_history_until`). |
| `market_context.py` | ✅ | Immutable snapshot for detectors. It already has an `atr` field, but nothing populates it. |
| `opportunity.py` | ✅ | `Opportunity`, `OpportunityType` (HIGH_BASE, **PULLBACK**, EMA_RIDE, FLAG, **FAILED_BREAKOUT**), `PatternState` |
| `constants.py` | ✅ | Daily-trend defaults |
| `enums.py`, `exceptions.py`, `logging.py` | ⬜ | |

### data/ (ingestion)
| File | State | Notes |
|---|---|---|
| `mt4_csv_loader.py` | ✅ | `Date,Time,O,H,L,C,V` → `list[Candle]`, **naive datetimes in broker server time** |
| `csv_loader.py` | ✅ | `timestamp,open,...` ISO → `list[Candle]`. It preserves offsets if present, so it can return a **mix of naive and aware datetimes**. |
| `market_loader.py` | 🟡 | Loads `USDJPY_{D1,H1,M15,M5}.csv` into `MarketData`. Filenames are hard-coded to USDJPY. |
| `yfinance_loader.py` | 🟡 | Converts to **America/New_York aware** timestamps. The dependency is undeclared. |
| `mt5_export_loader.py`, `yahoo_loader.py` | ⬜ | |

**Datasets on disk (USDJPY only, no EURUSD):**

| File | Range | Finding |
|---|---|---|
| `data/raw/USDJPY_D1.csv` | 2018-08-20 → 2026-07-10 | OK (~8 yrs) |
| `data/raw/USDJPY_H1.csv` | 2026-03-12 → 2026-07-10 | ~4 months |
| `data/raw/USDJPY_M15.csv` | 2026-06-08 → 2026-07-10 | ~1 month |
| `data/raw/USDJPY_M5.csv` | 2026-06-11 → 2026-07-10 | **Mislabeled: bars are 15 minutes apart, so this is M15 data.** It is also not tracked in git. |
| `data/historical/USDJPY_M5.csv` | 2026-04-19 → 2026-07-10 | yfinance-sourced, `-04:00` offsets, volume always 0, float32 artifacts (`158.99600219726562`) |

Every dataset holds a single price (bid or broker-chosen) with no ask, spread or tick data.

### indicators/
| File | State |
|---|---|
| `ema.py` | ✅ `calculate_ema(closes, period)` returns the full series, seeded with the first price |
| `atr.py`, `rsi.py` | ⬜ |

There is no Donchian/rolling-high/low helper.

### strategies/
| File | State | Notes |
|---|---|---|
| `strategy_base.py` | ✅ | `Strategy.generate_signal(market: MarketData, current_index: int)`. The signature is tied to `MarketData` and an m5 index. |
| `daily_trend_assessment.py` | 🟡 | Well tested and explainable. **Has a look-ahead bug (see §5).** |
| `trend_pullback_strategy.py` | 🟡 | The MVP shell. `generate_signal` returns `None` (H1/M15/M5 rules not built). |
| `ema_trend_strategy.py` | ❌ | `generate_signal` is decorated `@abstractmethod`, so **the class cannot be instantiated** (verified: `TypeError`). The SELL `return` is mis-indented and fires whenever the BUY branch doesn't. |
| `dummy_strategy.py` | 🟡 | Uses a different `generate_signal(candles)` signature than the base class |
| `breakout.py` | ⬜ | The natural home for Donchian |

### patterns/ + validation/ (research layer, the most mature part)
- `patterns/detector.py`: `PatternDetector` Protocol, `detect(MarketContext) -> Opportunity | None`.
- `patterns/high_base_detector.py`: rules HB-001…HB-007, fully traced.
- `validation/`: `RuleCheck`, `ContextReview`, `ResearchSummary`, per-detector explainers with a registry, plus console/CSV formatters for **TradingView side-by-side review**.
- `backtesting/signal_engine.py` + `signal_record.py`: runs detectors over contexts and records opportunities. **It explicitly does no trade simulation.**

### backtesting/ (trade simulation)
| File | State |
|---|---|
| `engine.py`, `metrics.py`, `report.py` | ⬜ empty |
| `signal_engine.py`, `signal_record.py` | ✅ detection-only |

`examples/demo_backtest.py` is the only "backtest". It **cannot run as written**:
`EMATrendStrategy` can't be instantiated, and it calls `generate_signal(history)`
with a list instead of `(market, index)`. Even if fixed, it fills at signal-bar
close and always exits at take-profit at the same timestamp, with no costs.

### risk/
| File | State | Notes |
|---|---|---|
| `position_sizer.py` | ✅ | Fixed-fractional sizing. `value_per_price_unit_per_lot` is supplied by the caller. **Directly reusable.** |
| `risk_manager.py` | ⬜-ish | `calculate_volume()` returns `1.0` |

### execution/ (broker integration)
| File | State | Notes |
|---|---|---|
| `executor_base.py` | ✅ | `execute(Order) -> Trade` (synchronous, one-shot) |
| `order_request.py` | ✅ | Broker-neutral order contract with side, type, volume, price, SL, TP and validation. **Reusable.** |
| `simulated_executor.py` | 🟡 | Fills instantly at `order.price` and exits at TP, with no time passing. Used by tests and demos only. |
| `backtest_executor.py`, `mt5_executor.py` | ⬜ | **There is no live broker integration.** |

### analytics/, config/, dashboard/, ml/
These are all empty. `analytics/performance.py`, `config/settings.py` and
`config/logging.yaml` exist with 0 bytes.

### mt5/
`ExportHistory.mq5` exports `CopyRates` to CSV. Its limitations:
- The filename is always `<Symbol>_M5.csv` whatever timeframe is selected.
- It drops `MqlRates.spread` and `real_volume`.
- It writes broker server time with no offset.
- It exports bid bars only.

### research/
`research/market_knowledge/` has a pattern-case template, 2 High Base cases and
empty `pullback/` and `failed_breakout/` folders. `research/schemas/*.md` are empty.

## 4. Data flow as it actually exists today

```
MT4 CSV (server time, single price)
        │  data/mt4_csv_loader.py
        ▼
list[Candle] ×4 ──► core.MarketData(daily,h1,m15,m5)
        │
        ├─► DailyTrendAssessment ─┐
        │                         ▼
        └─► examples/demo_signal_engine.build_h1_contexts ─► MarketContext
                                                                │
                                         HighBaseDetector ◄─────┘
                                                │
                                   SignalEngine → SignalRecord
                                                │
                              validation/ explainers → console / CSV review
```

The `Strategy → RiskManager → Executor → Trade → metrics` path is **not wired
end-to-end anywhere** in working code.

## 5. Correctness issues found during inspection

> **Status (2026-10-16):** items 1–6 were fixed in Phase 0. See
> [`phase0/PHASE0_REVIEW.md`](phase0/PHASE0_REVIEW.md) and ADR-003. Timestamps
> from different loaders (item 6) now fail loudly when mixed; full UTC
> normalization is Phase 1. Item 7 is still open.

These are recorded here, not fixed, because no code changes were requested.

1. **Look-ahead in `MarketData.daily_history_until` / `DailyTrendAssessment`.**
   The filter is `c.timestamp.date() <= t.date()`, so at any intraday time `t` the
   *current, unfinished* D1 bar (whose close is the end-of-day price) is included.
   The test `test_only_completed_candles_up_to_current_time_are_used` assumes this
   behavior. Every H1 context in `demo_signal_engine.py` therefore sees that
   day's closing price. **This affects existing High Base research results.**
2. **`h1_history_until` / `m15_history_until` also include the bar that opens at
   the floor of `t`.** That bar is not complete at `t` unless `t` is its close time.
3. `data/raw/USDJPY_M5.csv` contains M15 bars.
4. `EMATrendStrategy` can't be instantiated, and its SELL branch is mis-indented.
5. `demo_backtest.py` is broken (see above).
6. Timestamps are inconsistent across loaders: naive server time, NY-aware and
   offset-aware. Comparing naive and aware values raises `TypeError`, and mixing
   sources silently misaligns bars by hours.
7. `pandas`/`yfinance` are used or installed but not declared in `requirements.txt`.

## 6. Strengths worth preserving

- Clear separation of concerns, documented in code (detectors are read-only, and
  strategies don't size or execute).
- Explainability: rule-by-rule `RuleCheck`/`ContextReview` output designed for
  TradingView verification.
- Broker-neutral contracts (`OrderRequest`, `PositionSizer`) that already
  anticipate a backtest executor and an MT5 executor.
- A fast, deterministic, comprehensive unit test suite.
- Percent-of-price thresholds (instrument-independent), which matter for EURUSD
  (~1.1) vs USDJPY (~150).
