"""
Signal Engine demo, Strategy Validation Framework, and Research Report
Framework CLI.

Three modes:

1. Concise mode (default): scan historical H1 candles and report how
   many signals HighBaseDetector finds - unchanged from the original
   Signal Engine demo.
2. Review mode (--review / --export): a concise, TradingView-comparable
   PASS/FAIL explanation of every scanned MarketContext.
3. Research mode (--research): a much more detailed engineering report
   - every raw value, threshold, formula, and sub-rule outcome behind
   each PASS/FAIL, plus dataset/traceability sections and a rule-failure
   summary - intended for investigating a handful of examples at a time.

All three read the reusable validation framework in validation/ (see
validation/explainers.py and validation/validation_formatter.py). This
only explains detector behavior; it never changes it.

Example:

    python examples/demo_signal_engine.py \\
        --symbol USDJPY --timeframe H1 \\
        --start 2025-03-01 --end 2025-03-15 --limit 20 \\
        --research --export review.csv
"""

import argparse
from datetime import date, datetime

from backtesting.signal_engine import SignalEngine
from core.market_context import MarketContext
from data.market_loader import load_market_data
from indicators.ema import calculate_ema
from patterns.high_base_detector import HighBaseDetector
from strategies.trend_pullback_strategy import TrendPullbackStrategy
from validation.explainers import explainer_for
from validation.validation_formatter import (
    format_console_review,
    format_dataset_summary,
    format_research_review,
    format_research_summary,
    write_csv_export,
)
from validation.validation_report import DatasetSummary, build_research_summary

EMA20_HISTORY_WINDOW = 5
MIN_H1_CANDLES_FOR_CONTEXT = 50  # enough history for EMA50 + detector lookback
RESEARCH_MODE_SOFT_LIMIT = 20  # research mode is meant for a handful of examples


def build_h1_contexts(market, strategy) -> list[MarketContext]:
    """Build one MarketContext per completed H1 candle, from the point
    there is enough history to evaluate EMA50 onward."""
    contexts = []

    for i in range(MIN_H1_CANDLES_FOR_CONTEXT, len(market.h1)):
        candles = tuple(market.h1[: i + 1])
        closes = [c.close for c in candles]

        ema20_series = calculate_ema(closes, 20)
        ema50_series = calculate_ema(closes, 50)

        current_time = candles[-1].timestamp
        daily_assessment = strategy.daily_bias(market, current_time)

        contexts.append(
            MarketContext(
                symbol=candles[-1].symbol,
                timeframe="H1",
                timestamp=current_time,
                candles=candles,
                ema20=ema20_series[-1] if ema20_series else None,
                ema50=ema50_series[-1] if ema50_series else None,
                ema20_history=tuple(ema20_series[-EMA20_HISTORY_WINDOW:]),
                daily_assessment=daily_assessment,
            )
        )

    return contexts


def filter_contexts(
    contexts: list[MarketContext],
    start: date | None = None,
    end: date | None = None,
    limit: int | None = None,
) -> list[MarketContext]:
    """Restrict `contexts` to an inclusive [start, end] date range (by
    context timestamp date), then to the first `limit` of those, in
    chronological order."""
    filtered = [
        context
        for context in contexts
        if (start is None or context.timestamp.date() >= start)
        and (end is None or context.timestamp.date() <= end)
    ]

    if limit is not None:
        filtered = filtered[:limit]

    return filtered


def describe_empty_result(
    all_contexts: list[MarketContext],
    start: date | None,
    end: date | None,
) -> str:
    """Explain why --start/--end/--limit filtering left zero contexts to
    review, so a user isn't left staring at a silent "Evaluating 0 of N"
    line. Reports the dataset's available timestamp range plus the
    requested range, and calls out explicitly when the requested range
    falls entirely outside the data (the most common cause)."""
    if not all_contexts:
        return "No H1 MarketContexts are available in the loaded dataset."

    dataset_start = min(c.timestamp for c in all_contexts)
    dataset_end = max(c.timestamp for c in all_contexts)

    requested_start = start if start is not None else "(unbounded)"
    requested_end = end if end is not None else "(unbounded)"

    lines = [
        f"Dataset available range : {dataset_start} to {dataset_end}",
        f"Requested date range    : {requested_start} to {requested_end}",
        "",
    ]

    outside_range = (start is not None and start > dataset_end.date()) or (
        end is not None and end < dataset_start.date()
    )

    if outside_range:
        lines.append(
            "No contexts matched: the requested date range falls entirely "
            f"outside the available data ({dataset_start.date()} to {dataset_end.date()})."
        )
    else:
        lines.append("No contexts matched the given filters (check --limit).")

    return "\n".join(lines)


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid date '{value}': expected YYYY-MM-DD") from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Signal Engine over historical H1 candles, or review its "
            "detector reasoning for manual validation against TradingView."
        ),
    )
    parser.add_argument("--symbol", default="USDJPY")
    parser.add_argument(
        "--timeframe",
        default="H1",
        choices=["H1"],
        help="Only H1 MarketContexts are currently supported.",
    )
    parser.add_argument("--start", type=_parse_date, default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--end", type=_parse_date, default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=None, metavar="N")
    parser.add_argument(
        "--review",
        action="store_true",
        help="Print a full rule-by-rule review per MarketContext, for comparison against TradingView.",
    )
    parser.add_argument(
        "--research",
        action="store_true",
        help=(
            "Print a detailed engineering report per MarketContext - every raw value, "
            "threshold, formula, and sub-rule outcome - plus a dataset summary and rule-"
            "failure summary. Intended for investigating a handful of examples at a time."
        ),
    )
    parser.add_argument(
        "--signals-only",
        action="store_true",
        help="Only include MarketContexts where a signal was actually detected.",
    )
    parser.add_argument(
        "--export",
        default=None,
        metavar="PATH",
        help="Write a CSV review export to PATH (one row per reviewed MarketContext).",
    )
    return parser.parse_args(argv)


def build_dataset_summary(
    all_contexts: list[MarketContext],
    contexts: list[MarketContext],
    start: date | None,
    end: date | None,
) -> DatasetSummary:
    """Summarize the full dataset alongside how --start/--end/--limit
    narrowed it down to `contexts`, for the research report's opening
    "Dataset" section."""
    return DatasetSummary(
        first_context_timestamp=min((c.timestamp for c in all_contexts), default=None),
        last_context_timestamp=max((c.timestamp for c in all_contexts), default=None),
        contexts_available=len(all_contexts),
        requested_start=start,
        requested_end=end,
        contexts_selected=len(contexts),
    )


def print_signals(label: str, signals) -> None:
    print(f"{label}: {len(signals)} signal(s)")
    for record in signals:
        print(
            f"  {record.timestamp} {record.symbol} {record.timeframe} "
            f"[{record.detector}] {record.opportunity_type.value} "
            f"entry={record.entry_price:.5f} stop={record.stop_price:.5f} "
            f"quality={record.quality} confidence={record.confidence:.2f}"
        )
    print()


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    market = load_market_data("data/raw", symbol=args.symbol)
    strategy = TrendPullbackStrategy()
    detector = HighBaseDetector()

    print(f"Loaded {market}")

    all_contexts = build_h1_contexts(market, strategy)
    contexts = filter_contexts(all_contexts, start=args.start, end=args.end, limit=args.limit)

    if not contexts:
        print(describe_empty_result(all_contexts, args.start, args.end))
        return

    if args.research:
        summary = build_dataset_summary(all_contexts, contexts, args.start, args.end)
        print(format_dataset_summary(summary))
        print()

        if args.limit is None and len(contexts) > RESEARCH_MODE_SOFT_LIMIT:
            print(
                f"Note: research mode is meant for investigating a handful of examples "
                f"({len(contexts)} selected) - consider adding --limit.\n"
            )
    else:
        print(f"Evaluating {len(contexts)} of {len(all_contexts)} H1 MarketContexts\n")

    if args.review or args.export or args.research:
        explainer = explainer_for(detector)
        reviews = [explainer.explain(context) for context in contexts]

        if args.signals_only:
            reviews = [review for review in reviews if review.signal_detected]

        if args.review:
            for index, review in enumerate(reviews, start=1):
                print(format_console_review(review, index, len(reviews)))

        if args.research:
            for index, review in enumerate(reviews, start=1):
                print(format_research_review(review, index, len(reviews)))
            print(format_research_summary(build_research_summary(reviews)))
            print()

        if args.export:
            write_csv_export(reviews, args.export)
            print(f"Exported {len(reviews)} review row(s) to {args.export}")

        signal_count = sum(1 for review in reviews if review.signal_detected)
        print(f"{len(reviews)} context(s) reviewed, {signal_count} signal(s) detected.")
        return

    # Concise mode: unchanged from the original Signal Engine demo - just
    # the detected signals via SignalEngine, no rule-by-rule explanation.
    engine = SignalEngine()
    signals = engine.run(contexts, detectors=[detector])
    print_signals(detector.NAME, signals)


if __name__ == "__main__":
    main()
