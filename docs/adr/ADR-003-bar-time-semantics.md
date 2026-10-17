# ADR-003: Bar Time Semantics and the Closed-Candle Rule

**Status:** Accepted

**Date:** 2026-10-16

**Accepted:** 2026-10-16. The closed-candle rule and the split between `bar_open_time` and `signal_available_time` are implemented and tested. `core/timeframes.py` defines `candle_close_time` and `is_closed`. The `MarketData` time accessors use that rule. `SignalEngine` stamps `SignalRecord.signal_available_time`. Coverage is in `tests/test_timeframes.py` and `tests/test_market_data_lookahead.py`, and `docs/forex/phase0/PHASE0_REVIEW.md` records the behavior. `execution_time` is defined here and is still enforced only when a Phase 1 executor exists. That deferral is part of this decision, not an open proposal.

---

# Context

`MarketData.daily_history_until(t)` selected daily candles with
`timestamp.date() <= t.date()`. At any intraday time `t` that included the
current, still-forming daily candle, whose close is the END-of-day price.
The H1/M15 accessors had the same flaw for the bar opening at `floor(t)`.
Every H1 research context therefore saw that day's daily close (1998 of
1998 contexts in the bundled USDJPY data).

A candle's `timestamp` was also used ambiguously: sometimes as "the bar",
sometimes as "the moment we decided".

---

# Decision

## 1. Three distinct times

| Name | Meaning | Where it lives |
|---|---|---|
| `bar_open_time` | When a candle starts forming. `Candle.timestamp` is always this. A **label**, never a moment at which the bar's OHLC is known. | `Candle.timestamp`, `MarketContext.bar_open_time` |
| `signal_available_time` | When the candle closes (`bar_open_time + timeframe duration`). The earliest moment anything derived from it exists. | `core.timeframes.candle_close_time`, `MarketContext.signal_available_time`, `SignalRecord.signal_available_time` |
| `execution_time` | When an order based on that signal is filled. Decided by an executor only, and always **strictly after** `signal_available_time` (the next tradable price). | No executor exists yet. Enforced by the Phase 1 backtest engine. |

`MarketContext.timestamp`, `Opportunity.timestamp` and `SignalRecord.timestamp`
remain **labels** equal to the bar open time of the bar they describe. They
are kept for compatibility (CSV exports, TradingView comparison) and must not
be read as "available at".

## 2. The closed-candle rule

```
candle is visible at time t  <=>  candle.timestamp + duration(candle.timeframe) <= t
```

Every `MarketData` time accessor (`daily_at`, `h1_at`, `m15_at`, `m5_at`,
and the four `*_history_until`) applies this rule through
`core.timeframes.is_closed`. A strategy deciding at the close of bar X passes
`candle_close_time(X)`.

## 3. Clock

All comparisons happen on whatever single clock the data uses. The bundled
MT4 data uses naive broker server time. The rule is clock-agnostic, provided
candles and `t` share one clock. Mixing naive and tz-aware datetimes raises
`TypeError` (tested) rather than silently misaligning.

---

# Consequences

- Daily Bias during day D now uses day D-1, the last closed day. On the
  bundled data, 92 of 1998 H1 contexts changed DailyTrend (4 trend-flip days ×
  23 H1 bars). See `docs/forex/phase0/PHASE0_REVIEW.md`.
- The last H1 bar of a day (23:00 server time) closes exactly when the daily
  bar does, so it legitimately sees that day.
- **Conservative at session ends:** a Friday or holiday daily candle is
  treated as closing at the next server midnight, even if the market stopped
  earlier. This can delay information by up to one bar; it never leaks it.
- Local-time tz-aware timestamps across a DST change use Python's wall-clock
  `datetime + timedelta` arithmetic, which is wrong for intraday bars that
  span the change. Phase 1 normalizes to UTC, and the FX trading-day boundary
  becomes explicit configuration rather than "server midnight".
