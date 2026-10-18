# Forex Research Track: Validation Workflow

**Status:** Workflow approved by the user (`DECISIONS.md` D11). Stage 1 not
started. No Pine, Phase 1 Python or MQL5 code has been written for it.

Authority: [`DECISIONS.md`](DECISIONS.md) is binding. This file describes how
a Forex Research Track strategy moves from idea to execution validation. It
does not change any approved decision. Phase gates stay in
[`INTEGRATION_PLAN.md`](INTEGRATION_PLAN.md).

Scope: the Forex Research Track only, beginning with the Donchian H1 20/10
benchmark. The original MVP (Daily Bias → H1 Pullback → M15 Setup → M5
Trigger) and the High Base research are not affected. The empty MVP
placeholder `pine/trend_pullback_strategy.pine` is left untouched.

---

## 1. Stages

```
Stage 1  TradingView Pine Script   visual sanity check of the rules
   ↓     (no profitability evidence)
Stage 2  Python research framework  pandas + pyarrow + local Parquet,
   ↓                                transaction costs, out-of-sample,
   ↓                                walk-forward  →  research acceptance
Stage 3  MQL5 EA                    port of the accepted strategy only
   ↓
Stage 4  MT5 Strategy Tester        final real-tick execution validation
```

| Stage | Tool | Purpose | Gate to next stage |
|---|---|---|---|
| 1 | TradingView Pine Script (`pine/forex/donchian_h1_baseline.pine`) | Visual check that the written rules do what we think: channel levels, breakout bars, entry timing, 2 × ATR(14) stop, 10-bar exit, direction modes | Visual checklist (§2.3) passed and recorded. Required before Phase 2.3 (first Python baseline run). It doesn't block Phase 1 infrastructure work. |
| 2 | Python (Phases 1 and 2, later L6) | The research evidence: bid/ask M5 execution simulation, costs, out-of-sample, walk-forward, cost sensitivity, D08 metrics | **Research acceptance:** an explicit user decision based on the Python report. No automatic pass threshold. |
| 3 | MQL5 EA (L7) | Port the accepted rules to MT5 | EA compiles. Rules match the Python spec (same inputs, same signals on a shared window). |
| 4 | MT5 Strategy Tester, "Every tick based on real ticks" (L2) | Execution validation with broker ticks, spreads and contract specs | Trade-by-trade comparison with the Python ledger on the same window, with every difference explained |

The rule specification is written once, in the Python strategy spec (Phase
2.2). Pine and MQL5 are implementations of that spec. If they disagree, the
spec decides and the other implementation is fixed.

## 2. Stage 1: Pine visual sanity check

### 2.1 Proposed location

`pine/forex/donchian_h1_baseline.pine`

Why:
- `pine/` is the documented home for Pine source (`docs/project_structure.md`, Infrastructure layer).
- `forex/` mirrors `docs/forex/`. It keeps research scripts apart from the MVP placeholder in `pine/`.
- The file name states the benchmark and timeframe. Parameters live in the script header and inputs, not in the file name.

Pine is not Python code. It isn't imported or tested by `pytest`, and it adds
no dependency.

### 2.2 Script requirements

The script implements the approved baseline exactly (`FOREX_RESEARCH_TRACK.md`). It is not tuned.

| Item | Requirement |
|---|---|
| Version | Pine Script v6, `strategy()` |
| File | `pine/forex/donchian_h1_baseline.pine` |
| Chart | EURUSD **H1**. The script refuses to run on any other timeframe (`runtime.error`). |
| Parameters | Entry channel 20 completed H1 bars, exit channel 10 completed H1 bars, ATR length 14, initial stop 2 × ATR. Defaults are the approved baseline and are not tuned. |
| Signal confirmation | A breakout is confirmed only after the H1 bar has **closed**: the signal bar *t*'s close is above the highest high (long) or below the lowest low (short) of bars *t−20 … t−1*, i.e. `ta.highest(high, 20)[1]` / `ta.lowest(low, 20)[1]`. The bar is evaluated only on its final (confirmed) calculation, never on an intrabar or real-time update. |
| Signal time vs. execution time | **Signal time** = close of the signal bar (`time_close`). **Execution time** = the market fill at the open of the next H1 bar (`process_orders_on_close = false`), the earliest price after the signal is available. Both times are kept separately and shown in the entry label and trade comment. They are never conflated. |
| ATR capture | ATR(14) (`ta.atr`, RMA = Wilder) is **captured once, on the signal bar**, in a `var` variable when the signal is confirmed. That captured value sizes the initial stop. It is never re-read from later bars. |
| Initial stop | Placed relative to the **actual simulated entry fill price** (`strategy.position_avg_price`): long = fill − 2 × captured ATR, short = fill + 2 × captured ATR. It is set **once** after the fill and **never recalculated** on later H1 bars. To place the stop right after the fill, the script uses `calc_on_order_fills = true`. That recalculation only places the protective stop. It never evaluates new entry signals. |
| Exit channel | Opposite 10-bar channel. Long: the stop for bar *t+1* = max(current stop, lowest low of bars *t−9 … t*). Short: min(current stop, highest high of bars *t−9 … t*). Updated at each confirmed bar close. The stop **only tightens**. The initial ATR stop is the floor (long) / ceiling (short), never recomputed. |
| Take-profit | None |
| Direction | Input `LONG_ONLY` / `SHORT_ONLY` / `BOTH` |
| Positions | One open position at a time. `pyramiding = 0`. Entries are allowed only when `strategy.position_size == 0`, so an opposite breakout **never reverses** an open position (`strategy.entry` reverses by default). An opposite breakout while in a position is ignored, not queued. |
| Trade frequency | No fixed weekly (or other) trade limit |
| Sizing | **Diagnostic only, not broker-accurate.** Risk setting 0.25% of equity per trade (D05, unchanged until you approve a revision). Quantity = 0.25% × `strategy.equity` / (2 × captured ATR), in units, rounded down to 1,000 units (0.01 lot). Below 1,000 units the entry is skipped and labeled. It ignores spread, commission, slippage, the broker's contract specs and margin. The Python framework's sizing is authoritative. Pine sizing is never quoted as broker sizing. |
| Look-ahead / repaint | No `request.security`, no `lookahead_on`, no real-time-bar signals. Confirmed bars only. |
| Not allowed | Martingale, grid, averaging down, re-entry scaling, or any added filter |
| Plots | Upper/lower 20-bar entry channel, 10-bar exit channel, active stop line, signal markers (on the signal bar), fill markers (on the execution bar) with a reason label |

### 2.3 Visual checklist (Stage 1 acceptance)

Check on at least 10 trades per direction, including at least one each of: a
gap entry (Sunday open), a stop hit, a channel exit, and a breakout while a
position is already open.

1. Channel levels at 3 chosen bars match a manual count of the prior 20 / 10 bars.
2. Every entry is on the bar **after** a close beyond the prior channel. No entry on the breakout bar itself.
3. No entry occurs while a position is open. There are no reversals.
4. The initial stop equals the **fill price** ∓ 2 × the ATR(14) captured on the signal bar, and the initial stop doesn't move when later ATR values change.
5. The exit stop never loosens.
6. `LONG_ONLY` shows no shorts, `SHORT_ONLY` no longs, and `BOTH` shows both.
7. Signals don't change after reloading the chart (no repaint).
8. Every trade shows a signal time (signal-bar close) earlier than or equal to its execution time (next-bar open fill).
9. The protective stop is active on the fill bar itself (`calc_on_order_fills`). If TradingView's emulator turns out not to support this on historical bars, record it as a known Pine limitation in the sanity-check record. Don't work around it by placing the stop from an estimated entry.

The result is recorded in `docs/forex/pine/PINE_SANITY_CHECK.md`: TradingView
symbol and feed, chart timezone, date window, checklist outcome, and
screenshots or the exported "List of trades" for later comparison with Python.

### 2.4 What Stage 1 does **not** show

**Pine Strategy Tester results do not prove profitability.** They are not
research evidence under D08, and no report, commit message or document may
present them as such. Pine net profit, profit factor or drawdown may be
written down for context only, labeled "TradingView Strategy Tester, visual
sanity check, not evidence". Reasons: a single price series without bid/ask,
limited history depth, a coarse intrabar model, no out-of-sample or
walk-forward split, and costs that differ from the Python model (§4).

## 3. Stage 2: Python research framework

The approved Phase 1/Phase 2 plan with these approved points (D11):

- **Storage:** local **Parquet** files (pandas + pyarrow) outside Git, under `AQTF_MARKET_DATA_ROOT`, with the manifest JSON (source timezone, hashes, row counts) beside them. Raw downloads also stay outside Git.
- **Data:** EURUSD **M5 bid/ask** is the preferred dataset. M1 bid/ask is optional and resampled to M5 only when direct M5 is unavailable or unsuitable. H1 signal bars are derived from validated M5 data (D03, D07).
- **Costs:** spread from bid/ask data, commission, slippage with sensitivity. Swap is not modeled in v1 and is stated in every report.
- **Validation:** in-sample / out-of-sample split, walk-forward validation and cost sensitivity (D08). Report the D08 metrics.
- **Unchanged:** H1 Donchian 20/10, 2 × ATR(14), `LONG_ONLY` / `SHORT_ONLY` / `BOTH`, 0.25% risk cap with min-lot skip, no weekly trade limit, no martingale or grid.

Research acceptance is a user decision recorded in `DECISIONS.md`. Until then,
no profitability claim is made (D02, D08).

## 4. TradingView vs. Python execution assumptions

Pine and Python trade lists are **expected to differ**. Stage 1 checks rule
logic, not P&L. The differences below explain the expected mismatches.

| Area | TradingView Pine (Stage 1) | Python research framework (Stage 2) | Effect on comparison |
|---|---|---|---|
| Data source | The chart symbol's feed (e.g. `OANDA:EURUSD`, `FX:EURUSD`). Broker-specific, usually one price per bar (bid or mid, depending on the feed). | Dukascopy bid **and** ask, normalized to UTC | Channel and ATR values differ by fractions of a pip. Breakouts near the channel can appear in one and not the other. |
| Price side | One series. Entries, stops and exits all use it. | Long entry at ask, long stop on bid low. Short entry at bid, short stop on ask high. | Python fills are worse by the spread. A short can be stopped out by spread alone in Python but not in Pine. |
| Spread | Not modeled | From bid/ask data | Pine P&L is optimistic |
| Commission | Strategy property (cash per order / per contract) | $3.50 per lot per side (D6, proposed) | Set Pine to an equivalent value if comparing, but expect rounding differences |
| Slippage | Fixed ticks on market/stop orders | 0.2 pip default, sensitivity 0.2 / 0.5 / 1.0 pip | Not comparable beyond the default |
| Swap | Not modeled | Not modeled in v1, stated in the report | Same gap in both |
| Entry fill timing | Signal at the H1 close, market fill at the next H1 bar open | Signal available at the H1 close, fill at the open of the M5 bar starting at that time (PHASE1_PLAN C3) | Same instant. Price differs only by feed and side. |
| Initial stop reference | Fill price (single series) ∓ 2 × ATR captured on the signal bar, set once | Phase 2.2 spec (to be written). It must use the same rule: actual fill (ask for longs, bid for shorts) ∓ 2 × signal-bar ATR, set once. | The same rule, but the Python fill includes spread and slippage, so stop levels differ by those amounts |
| Stop on the fill bar | Active right after the fill via `calc_on_order_fills` (to be verified in P.1) | Evaluated from the entry fill onward within the same M5 bar (PHASE1_PLAN, executor) | If Pine can't protect the fill bar, early stop-outs can differ |
| Intrabar path | Broker emulator assumes a path inside each H1 bar (open → nearer extreme → other extreme → close), unless Bar Magnifier is enabled | M5 bars inside the H1 bar. Within an M5 bar, stop-first when ambiguous. | Stop and exit timing inside a volatile H1 bar can differ |
| Gaps | Stop fills at the gap open | Stop fills at the M5 bar open | Similar. Prices differ by feed. |
| Timestamps | Bar open time in the chart timezone | Bar open time in UTC | Compare in UTC. Set the chart timezone to UTC for Stage 1. |
| Trading day / weekly open | Defined by the symbol's session | Configurable, 17:00 America/New_York | Doesn't move H1 bars. It affects the first bar of the week and D1 bars, which this baseline doesn't use. |
| Weekend / filler bars | Feed-specific | Dukascopy flat filler bars are dropped and counted | Prior-bar windows can cover different bars around weekends and holidays |
| ATR warm-up | RMA seeded from the start of the loaded history | Wilder ATR seeded from the start of the stored data | Early values differ. Ignore the first 100 bars of either history. |
| History depth | Limited by the TradingView plan. May not reach back to 2015. | EURUSD 2015–2025 | Pine can't cover the full research period |
| Position sizing | Diagnostic only, not broker-accurate: units from 0.25% of `strategy.equity` / (2 × ATR), no spread or costs in the risk distance | Lots rounded down to 0.01, 0.25% cap with the slippage assumption in the risk distance, min-lot skip, broker contract specs | Pine quantities aren't comparable to broker lots. Python sizing is authoritative. |
| Equity | `strategy.equity` includes open P&L | Sizing on current equity as defined in Phase 1 | Small size differences |
| Out-of-sample / walk-forward | None | Required (D08) | Only Python produces research evidence |

## 5. Stages 3 and 4: MQL5 EA and MT5 Strategy Tester

- **No MQL5 EA code is written before research acceptance** (Stage 2 gate, L7).
- The EA ports the accepted Python spec without additions. 0.25% risk, min-lot skip, one position, no martingale or grid.
- MT5 Strategy Tester in "Every tick based on real ticks" mode is the final execution check (L2). It is compared trade by trade with the Python ledger on the same window. Expected sources of difference: broker feed vs. Dukascopy, broker spreads and commission, broker day boundary (`phase0/PHASE0_REVIEW.md` §2), and contract specs.
- A passing MT5 test validates execution, not future profitability.
