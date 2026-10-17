# Phase 0 Review: Correctness and Regression Tests

Date: 2026-10-16 · Branch: `fix/phase0-correctness` (from `feature/trading-memory-v1` @ `2f07cba`)

Scope: fix look-ahead in multi-timeframe access, verify and correct
mislabeled USDJPY data, and repair `EMATrendStrategy` / `demo_backtest.py`.
No Phase 1 work (no new data sources, no execution simulation, no Donchian).

---

## 1. MarketData time accessors (all eight)

| Method | Before | After |
|---|---|---|
| `daily_at(t)` | D1 bar with the same **date** as `t` (forming bar) | latest D1 bar with `open + 1d <= t` |
| `h1_at(t)` | H1 bar with the same date+hour (forming bar) | latest H1 bar with `open + 1h <= t` |
| `m15_at(t)` | M15 bar of the same quarter-hour (forming bar) | latest M15 bar with `open + 15m <= t` |
| `m5_at(t)` | did not exist | latest M5 bar with `open + 5m <= t` |
| `daily_history_until(t)` | `date <= t.date()`, so it **included today's bar** | closed bars only |
| `h1_history_until(t)` | `open <= floor_hour(t)`, so it **included the forming bar** | closed bars only |
| `m15_history_until(t)` | `open <= floor_15m(t)`, so it **included the forming bar** | closed bars only |
| `m5_history_until(t)` | did not exist | closed bars only |

All eight go through one rule, `core.timeframes.is_closed`. Tests
(`tests/test_market_data_lookahead.py`) check each one at open time,
close − 1 s, close time, with `lookback`, and before the first close.

Direct attribute access (`market.h1[i]`, `market.m5[: i + 1]`) is
index-based and is not covered by the rule. The caller decides which
index is closed. `EMATrendStrategy` and `build_h1_contexts` treat index
`i` as "decide at the close of bar i", which is correct as long as
execution happens after that close.

## 2. Daily close, server clock, New York 17:00 and DST

**Empirical finding on the bundled MT4 data** (aligned against the
tz-aware yfinance USDJPY series for 2026-04-20 → 2026-07-10, during US DST):

| Assumed server offset | Mean abs. H1 close diff |
|---|---|
| UTC+1 | 0.0678 |
| **UTC+2** | **0.0139** |
| UTC+3 | 0.0666 |

- In summer the server clock is **UTC+2**, so D1 bars open at 00:00 server =
  22:00 UTC = **18:00 New York**, not 17:00. The 17:00–18:00 NY hour
  belongs to the previous D1 bar.
- Weeks run Mon 00:00 → Fri 22:00 (last H1 bar). There are no Sunday D1 bars.
- Winter offset could not be verified (no overlapping reference data). If
  the server is fixed UTC+2, winter D1 bars start at 17:00 NY.
- **Implication:** daily values from this broker may differ from TradingView's
  FX daily bars during US summer time. That's a verification caveat for the
  existing Daily Bias checks, not a leak.

**Why the fix is still correct:** candles and `t` are compared on the same
naive server clock, and a D1 bar spans 00:00 → 00:00 on that clock
regardless of DST. That's tested on a US DST-change date.

**Conservative edge:** the Friday D1 bar is treated as closing at Saturday
00:00 server time, although trading stops at 23:00. The final Friday H1
context (22:00 bar, available 23:00) therefore uses Thursday's D1. This
delays information and never leaks it.

**Not solved in Phase 0:** tz-aware *local* (e.g. America/New_York)
timestamps across a DST change use wall-clock `datetime + timedelta`
arithmetic, which is wrong for intraday bars spanning the change. Nothing in
`MarketData` uses such data today. Phase 1 normalizes to UTC and makes the
trading-day boundary configurable. Mixing naive and aware times raises
`TypeError` (tested).

## 3. build_h1_contexts time semantics (ADR-003)

| Concept | Value for an H1 context | Field |
|---|---|---|
| bar_open_time | H1 candle open (label shown on TradingView) | `context.timestamp`, `context.bar_open_time` |
| signal_available_time | H1 candle close = open + 1h | `context.signal_available_time`, `SignalRecord.signal_available_time` |
| execution_time | not defined in Phase 0 (no executor); must be > signal_available_time | Phase 1 engine |

Daily Bias is evaluated at `signal_available_time`. `SignalEngine` now
stamps every `SignalRecord` with `signal_available_time`, so a downstream
simulator never has to infer it from the bar-open label. `Opportunity`,
the High Base detector and the CSV exports are unchanged.

## 4. The 92 changed DailyTrend contexts

Full row-level record: [`daily_trend_changes.csv`](daily_trend_changes.csv),
covering every changed context with before/after daily candle, bias and strength.
It was produced by running the original code (`2f07cba`, in a temporary
worktree) and the fixed code over the same 1998 H1 contexts.

- Before: **1998 / 1998** contexts used the same-day (forming) D1 candle.
- After: 67 contexts use the same-day D1 candle, all of them **23:00 H1
  bars**, which close exactly when the D1 bar does (legitimate).
- 92 contexts changed bias/strength: 46 FAIL→PASS and 46 PASS→FAIL.
  There were no strength-only changes.

| Day | H1 contexts | Before (D1 used) | After (D1 used) |
|---|---|---|---|
| 2026-04-17 | 23 | NEUTRAL/NONE (04-17) | BULLISH/STRONG (04-16) |
| 2026-04-21 | 23 | BULLISH/STRONG (04-21) | NEUTRAL/NONE (04-20) |
| 2026-04-30 | 23 | NEUTRAL/NONE (04-30) | BULLISH/STRONG (04-29) |
| 2026-05-19 | 23 | BULLISH/STRONG (05-19) | NEUTRAL/NONE (05-18) |

These are the four trend-flip days in the sample. Previously the bias
flipped at the *start* of the day using that day's not-yet-known close. Now
it flips one day later, when that close is actually known. The High Base
detector still finds 0 signals in both versions, so no research conclusion
changes, but any manual TradingView comparison made on these four days
should be re-checked.

## 5. MVP and High Base logic

No changes to `patterns/`, `validation/`, `models/`, `indicators/`, `risk/`,
`execution/`, `strategies/trend_pullback_strategy.py`,
`strategy_base.py` or `dummy_strategy.py`. `daily_trend_assessment.py`
changed in its docstring only. The relevant suites pass: High Base detector,
explainer, research report, validation formatter and daily trend (117 tests).
Behavior changes only through the corrected `MarketData` input.

## 6. Data corrections

- `data/raw/USDJPY_M5.csv`: all 2048 rows are byte-identical to rows of
  `USDJPY_M15.csv` (15-minute spacing). Removed with `git rm`; it remains
  recoverable from history. No real USDJPY M5 data exists in the repo.
- `load_market_data` reads `<symbol>_<TF>.csv` (previously always `USDJPY_*`,
  so `--symbol EURUSD` silently loaded USDJPY). M5 is optional. Each file's
  spacing must match its label, otherwise `ValueError`.
- `mt5/ExportHistory.mq5`: the filename now includes the real timeframe.
  **UNCOMPILED / UNVERIFIED.** It was written without MetaEditor or an MT5
  terminal, and is marked as such in the file header. That this script
  produced the mislabeled file is a plausible root cause, not a proven one.

## 7. Test quality

- 205 test functions (was 170). Every test contains at least one assertion.
  Two "must not raise" tests were made explicit with `assertIsNone`.
- **Old code:** the new look-ahead and daily-trend tests produce 30 failures
  against the original `MarketData` and context builder.
- **Mutation check:** 15 deliberate bugs were injected one at a time and the
  full suite was run each time. **All 15 were caught.**

| Injected bug | Failing tests |
|---|---|
| closed boundary `<=` → `<` | 19 |
| old leaky rule (`open <= t`) | 36 |
| old date-based daily rule | 11 |
| `*_at` ignores close time | 11 |
| `m5_*` reads M15 list | 3 |
| lookback off-by-one | 4 |
| context builder evaluates at bar open | 1 |
| `signal_available_time` = bar open | 2 |
| `SignalEngine` drops `signal_available_time` | 1 |
| spacing check disabled | 2 |
| duplicate-timestamp check disabled | 1 |
| loader hard-codes USDJPY | 3 |
| M5 required again | 3 |
| EMA SELL mis-indent restored | 1 |
| EMA BUY close>EMA20 condition dropped | 1 |

## 8. Unresolved risks

1. **Broker day boundary ≠ 17:00 NY in summer** for the bundled data, so
   TradingView daily comparisons can disagree. To be addressed by Phase 1
   configurable boundaries. Existing "Verified" entries in `docs/strategy.md`
   were not re-checked.
2. **Local-tz DST arithmetic** is unsafe for aware non-UTC intraday data
   (§2). Not used today; Phase 1 normalizes to UTC.
3. **Index-based access** (`market.m5[: i + 1]`) bypasses the closed-candle
   rule by design. Any future executor must fill strictly after the bar
   at index `i` closes.
4. **No real USDJPY M5 data.** Demos now use M15. Re-export M5 if needed.
5. **MQL5 exporter unverified** (§6).
6. **`EMATrendStrategy` output volume:** it prints a banner per qualifying
   bar (~255k lines in `demo_backtest.py`). This is existing behavior and
   was left unchanged.
7. **`demo_backtest.py` remains unrealistic** (instant TP fills, no costs).
   It is labeled as such.
