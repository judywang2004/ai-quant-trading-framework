# Gap Analysis: Forex EA Research

Target capability: research and backtest **EURUSD / USDJPY Donchian Breakout**
and **Failed Pullback Continuation** with results realistic enough to decide
whether an MT5 EA is worth building.

First vertical slice: **EURUSD historical data → Donchian signals → realistic
backtest → performance report.**

See `CURRENT_ARCHITECTURE.md` for the inventory this builds on.

> **Updated after approval (2026-10-16):** approved decisions are in
> [`FOREX_RESEARCH_TRACK.md`](FOREX_RESEARCH_TRACK.md) and take precedence. Notably:
> execution is simulated on **M5** (resampled from Dukascopy M1), the stop is
> 2 × ATR(**14**), risk is capped at **0.25%** with min-lot skipping, and there is
> no fixed weekly trade limit. The look-ahead and data issues in §2.2 and
> `CURRENT_ARCHITECTURE.md §5` were fixed in Phase 0.

---

## 1. Summary

| Capability | Have | Gap | Slice needs it? |
|---|---|---|---|
| Historical data: EURUSD | none | everything | **Yes** |
| Historical data: Bid **and** Ask | none (single price) | new bar model + source | **Yes** |
| Long history (≥ 5 yrs intraday) | USDJPY D1 only | M1 source | **Yes** |
| Timestamp normalization | 3 incompatible conventions | UTC policy + converters | **Yes** |
| Data quality checks | none | gaps, duplicates, spread sanity | **Yes** (minimal) |
| Resampling M1 → M5/H1/D1 | none | resampler with configurable FX day boundary | **Yes** |
| Indicators: Donchian, ATR | EMA only (`atr.py` empty) | 2 functions | **Yes** |
| Donchian strategy | `strategies/breakout.py` empty | strategy | **Yes** |
| Instrument spec (pip, contract, quote ccy) | none | small model | **Yes** |
| Transaction costs | none | spread (from data), commission, slippage, swap | **Yes** (swap optional in v1) |
| Event-driven execution sim | `backtesting/engine.py` empty | engine | **Yes** |
| Position management (trailing exit) | none | minimal PositionManager | **Yes** |
| Position sizing | ✅ `PositionSizer` | quote→account ccy conversion | **Yes** (reuse) |
| Performance metrics / report | `analytics/`, `metrics.py`, `report.py` empty | metrics + report | **Yes** |
| Failed Pullback Continuation | Opportunity types + detector framework | rule spec + detector | No (phase 2) |
| USDJPY realistic test | partial data | JPY P&L conversion, data | No (phase 2) |
| Live MT5 execution | none | `mt5_executor.py` | No |
| Walk-forward / robustness | none | later | No |

## 2. Detailed gaps

### 2.1 Historical Bid/Ask data

**Today:** every bar has one OHLC series. MT4/MT5 exports are bid-based by
convention, and the yfinance data is undocumented mid-ish with zero volume.
There is no EURUSD data at all.

**Why it matters:** Donchian breakouts on H1 trade around the very highs and lows
where the spread widens (rollover at 17:00 New York, news). A long entry fills
at the **ask** and a long stop triggers on the **bid**. With a single price series,
backtests systematically understate cost and overstate the win rate on tight
stops. For EURUSD a typical 0.1–0.3 pip ECN spread is small per trade, but
rollover-hour spreads of 1–3+ pips land exactly when an H1 bar closes.

**Needed:**
- A `QuoteBar` (bid OHLC + ask OHLC, or bid OHLC + spread per bar) that
  doesn't replace `Candle` but can produce a bid, ask or mid `Candle` view for
  existing indicator code.
- **Source:** Dukascopy historical data provides separate **BID and ASK M1**
  exports in GMT going back to 2003 for majors. It's free and the de-facto
  research standard. The secondary source is an MT5 export that includes
  `MqlRates.spread`. That gives the minimum spread per bar from the broker you
  will actually trade on, which is useful for calibrating, not as the primary series.
- Storage outside git (~10–15 MB/year/symbol gzipped at M1 for both sides).

### 2.2 Timestamp normalization

**Today:**
| Loader | Output |
|---|---|
| `mt4_csv_loader` | naive, broker server time (usually UTC+2/+3, DST-shifted) |
| `csv_loader` | whatever the file says (naive or offset-aware) |
| `yfinance_loader` | aware, America/New_York |

**Needed:**
- One rule: **all stored and engine timestamps are tz-aware UTC and mark bar
  open time.**
- Each source loader converts at the boundary, given the source's zone (e.g.
  `Europe/Athens`-like DST behavior for typical MT servers, or a fixed offset).
- **FX trading day:** D1 and H4 bars are built with the day rolling at
  **17:00 America/New_York** (the industry convention that gives 5 daily bars
  per week, no Sunday stub). This must be explicit, because a UTC-midnight D1
  produces a 6th "Sunday" bar and different Donchian levels than MT5 or
  TradingView show.
- Session helpers (e.g. "skip entries 16:55–17:10 NY") derived from UTC via
  `zoneinfo`, which is stdlib, so no new dependency is needed.
- **Bar completeness:** a bar is usable by a strategy only once
  `now >= bar.open_time + bar.duration`. This is the fix for the look-ahead
  issue documented in `CURRENT_ARCHITECTURE.md §5`, applied in the new
  code path. *(Phase 0 applied the same rule to the existing `MarketData`;
  see ADR-003.)*

### 2.3 Data quality

**Needed (minimal for slice):** on import, report and reject
- duplicate or non-monotonic timestamps
- `ask < bid` or a spread above a configurable cap (bad ticks)
- `high < max(open, close)` or `low > min(open, close)`
- gaps outside the expected weekend or holiday closure (report, don't fill)

The output is a short data-quality summary printed with every backtest so that
results are traceable to the data they ran on.

### 2.4 Indicators

- `donchian(highs, lows, period)` returns upper and lower channels computed from
  **prior** completed bars only (excluding the current bar, so that "close above
  channel" is meaningful).
- `atr(highs, lows, closes, period)` uses Wilder smoothing (matches MT5 `iATR`
  and TradingView `ta.atr`), and fills the existing empty `indicators/atr.py`.
  `MarketContext.atr` is already waiting for it. Approved period: **14**.

### 2.5 Strategy interface fit

`Strategy.generate_signal(market: MarketData, current_index: int)` assumes a
fixed D1/H1/M15/M5 `MarketData` indexed on M5. A single-timeframe Donchian on
H1/H4 doesn't fit that without either faking `MarketData` or changing the
base class.

`Signal.take_profit` is a required `float`. Classic Donchian has **no take
profit**; it exits on an opposite-channel trailing stop.

### 2.6 Transaction-cost modeling

| Component | Model for slice | Source of numbers |
|---|---|---|
| Spread | **Implicit**: fill buys at ask, sells at bid from the data | `QuoteBar` |
| Commission | Per lot per side in account ccy (e.g. $3.50/side/100k, configurable) | Broker schedule |
| Slippage | Fixed pips added adversely on market and stop fills (default 0.2 pip EURUSD, configurable). Stop orders that gap fill at the bar's open, not the stop price. | Assumption; sensitivity-test 0 / 0.5 / 1.0 |
| Swap / rollover | Per-lot-per-night long/short rates, triple on Wednesday (v1 can be a config of fixed rates) | Broker swap table |
| Spread floor / markup | Optional: `max(data_spread, min_spread)` to mimic a retail account wider than Dukascopy | Broker comparison (MT5 `spread` export) |

The report must show **gross P&L, each cost bucket and net P&L** separately. A
strategy that only works at zero cost is the most common false positive in FX
research.

### 2.7 Event-driven execution simulation

**Today:** `SimulatedExecutor` fills at signal price and exits at TP in zero time.

**Needed:** a deterministic bar-event engine with an explicit order of events:

```
for each M5 QuoteBar (UTC, chronological):
  1. Fill pending orders whose trigger is reached in this bar
     (MARKET → this bar's open; STOP → trigger or open if gapped through)
  2. Check open positions' stop / target on this bar
     (longs vs BID high/low, shorts vs ASK high/low;
      if both SL and TP are touched in one bar → assume SL first: conservative,
      because M5 OHLC does not reveal the intrabar order)
  3. Mark-to-market equity (at close bid/ask)
  4. If this bar completes a signal-timeframe bar (e.g. H1):
       a. append completed H1 bar to history
       b. PositionManager updates trailing stops (from completed bars only)
       c. Strategy evaluates completed history → Signal | None
       d. Risk sizing (≤ 0.25% equity; skip if min lot exceeds it)
          → OrderRequest queued for NEXT bar (step 1)
  5. Apply swap if this bar crosses 17:00 NY rollover
```

Required properties:
- **No same-bar fill of a signal computed from that bar's close.** The earliest
  fill is the next M5 bar's open at the ask or bid plus slippage.
- Weekend gaps are handled naturally by "fill at open if gapped".
- A single position per symbol for v1. `PositionManager` blocks duplicates.
- Deterministic: same data and config produce byte-identical trade list.

M5 execution resolution (approved) with H1 signal resolution makes the
"which came first, SL or TP" ambiguity uncommon but not impossible. The
adverse assumption above is the documented resolution. M1 data stays
available for spot-checking ambiguous bars later.

**Performance:** 10 years of EURUSD M5 is ~740k bars (M1 raw: ~3.7M per side,
read only during resampling). To keep memory bounded, the engine should
**stream bars year by year** (iterator) and keep only a bounded window of
signal-timeframe bars. Pure Python at that scale is expected to run in minutes,
which is acceptable for research. Optimization is deferred per `CLAUDE.md`.

### 2.8 Position sizing and currency conversion

`PositionSizer` is reusable as is. What's missing is computing
`value_per_price_unit_per_lot` per instrument and account currency:
- **EURUSD, USD account:** quote ccy = USD, so 1.0 price unit × 100,000 =
  $100,000 per lot. This is constant.
- **USDJPY, USD account:** quote ccy = JPY, so value = 100,000 / USDJPY_price.
  It varies per bar, and P&L in JPY must be converted at the exit-time rate.

This needs an `Instrument` spec: symbol, base/quote ccy, contract size, pip
size, digits and min lot/step. **If the minimum lot (after rounding down to
the lot step) would risk more than 0.25% of equity, the trade is skipped and
counted, never rounded up.**

### 2.9 Performance reporting

**Needed:**
- **Trade list CSV:** entry/exit time (UTC), side, lots, entry/exit price,
  gross P&L, spread cost, commission, slippage, swap, net P&L, R-multiple,
  MAE/MFE, and exit reason.
- **Equity curve CSV:** daily equity, realized and marked-to-market.
- **Required metrics (approved):** actual trade frequency per **week** and per
  **month**, **net expectancy in R**, **maximum drawdown**, and the count of
  trades skipped by the min-lot / 0.25% risk rule.
- **Further metrics:** net profit, CAGR, max drawdown (abs and %), Sharpe and Sortino
  (daily returns), profit factor, win rate, avg win/loss, expectancy (R),
  trade count, avg holding time, exposure %, longest losing streak, and
  **costs as % of gross profit**.
- A **per-year breakdown** to spot regime dependence.
- **Header:** data source, date range, data-quality summary, full config
  (strategy params plus cost model) for reproducibility.
- An optional equity/drawdown PNG via matplotlib, which is already a dependency.

### 2.10 Failed Pullback Continuation (later work, L5)

**Reusable as is:** `PatternDetector` protocol, `MarketContext` (with `atr`),
`Opportunity` (`PULLBACK`/`FAILED_BREAKOUT` types already exist), `SignalEngine`
for detection-only validation, `validation/` explainers for TradingView review,
and `research/market_knowledge/{pullback,failed_breakout}/` for case notes.

**Missing:**
- **A written rule specification.** "Failed pullback continuation" has several
  common definitions (e.g. a pullback that fails to reach a level and resumes;
  a failed counter-trend break that resumes the trend). This needs rule IDs like
  HB-001…HB-007 before any code.
- A bridge from `Opportunity` (READY/TRIGGERED) to `Signal`/`OrderRequest` so
  detector output can be traded in the same engine as Donchian.

### 2.11 Verification and trust

- **Donchian levels:** spot-check against TradingView `ta.highest/ta.lowest`
  on the same bars, per the project's verification rule.
- **Engine behavior:** hand-built fixtures with known outcomes (gap-through
  stop, SL and TP in same bar, rollover swap, next-bar fill).
- **Cross-check:** run the same rules in the MT5 Strategy Tester ("Every tick
  based on real ticks") over a short period. Trade count and direction should
  match closely, and P&L should be in the same ballpark. Exact match isn't
  expected because of different data feeds.

## 3. Not gaps (deliberately out of scope for the slice)

Live/paper MT5 execution, portfolio of multiple symbols, parameter optimization,
walk-forward, Monte Carlo, ML filters, DuckDB/Parquet storage, dashboard, and the
Trading Memory schema. All of these come after a single honest backtest exists.
