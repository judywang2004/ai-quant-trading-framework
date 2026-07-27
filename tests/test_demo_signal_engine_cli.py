import argparse
import unittest
from datetime import date, datetime, timedelta

from core.market_context import MarketContext
from examples.demo_signal_engine import (
    build_dataset_summary,
    describe_empty_result,
    filter_contexts,
    parse_args,
)
from models.candle import Candle


def _context(index: int) -> MarketContext:
    timestamp = datetime(2025, 3, 1) + timedelta(hours=index)
    candle = Candle(
        symbol="USDJPY",
        timeframe="H1",
        timestamp=timestamp,
        open=100.0,
        high=100.5,
        low=99.5,
        close=100.2,
        volume=0.0,
    )
    return MarketContext(symbol="USDJPY", timeframe="H1", timestamp=timestamp, candles=(candle,))


class ParseArgsTests(unittest.TestCase):
    def test_defaults(self):
        args = parse_args([])

        self.assertEqual(args.symbol, "USDJPY")
        self.assertEqual(args.timeframe, "H1")
        self.assertIsNone(args.start)
        self.assertIsNone(args.end)
        self.assertIsNone(args.limit)
        self.assertFalse(args.review)
        self.assertFalse(args.research)
        self.assertFalse(args.signals_only)
        self.assertIsNone(args.export)

    def test_parses_all_supported_arguments(self):
        args = parse_args(
            [
                "--symbol", "EURUSD",
                "--timeframe", "H1",
                "--start", "2025-03-01",
                "--end", "2025-03-15",
                "--limit", "20",
                "--review",
                "--research",
                "--signals-only",
                "--export", "review.csv",
            ]
        )

        self.assertEqual(args.symbol, "EURUSD")
        self.assertEqual(args.start, date(2025, 3, 1))
        self.assertEqual(args.end, date(2025, 3, 15))
        self.assertEqual(args.limit, 20)
        self.assertTrue(args.review)
        self.assertTrue(args.research)
        self.assertTrue(args.signals_only)
        self.assertEqual(args.export, "review.csv")

    def test_rejects_invalid_date_format(self):
        with self.assertRaises(SystemExit):
            parse_args(["--start", "03/01/2025"])

    def test_rejects_unsupported_timeframe(self):
        with self.assertRaises(SystemExit):
            parse_args(["--timeframe", "M15"])

    def test_review_and_signals_only_default_false(self):
        args = parse_args(["--limit", "5"])

        self.assertFalse(args.review)
        self.assertFalse(args.signals_only)

    def test_research_flag_parses_independently_of_review(self):
        args = parse_args(["--research"])

        self.assertTrue(args.research)
        self.assertFalse(args.review)


class FilterContextsTests(unittest.TestCase):
    def setUp(self):
        # 5 hourly contexts: 2025-03-01 00:00 .. 04:00
        self.contexts = [_context(i) for i in range(5)]

    def test_no_filters_returns_everything(self):
        result = filter_contexts(self.contexts)

        self.assertEqual(result, self.contexts)

    def test_start_date_is_inclusive(self):
        result = filter_contexts(self.contexts, start=date(2025, 3, 1))

        self.assertEqual(len(result), 5)

    def test_start_date_excludes_earlier_contexts(self):
        contexts = [_context(i) for i in range(-24, 24, 12)]  # spans two days
        result = filter_contexts(contexts, start=date(2025, 3, 1))

        self.assertTrue(all(c.timestamp.date() >= date(2025, 3, 1) for c in result))
        self.assertLess(len(result), len(contexts))

    def test_end_date_is_inclusive(self):
        result = filter_contexts(self.contexts, end=date(2025, 3, 1))

        self.assertEqual(len(result), 5)

    def test_end_date_excludes_later_contexts(self):
        contexts = [_context(i) for i in range(0, 48, 12)]  # spans two days
        result = filter_contexts(contexts, end=date(2025, 3, 1))

        self.assertTrue(all(c.timestamp.date() <= date(2025, 3, 1) for c in result))
        self.assertLess(len(result), len(contexts))

    def test_start_and_end_combine_as_inclusive_range(self):
        contexts = [_context(i) for i in range(0, 96, 24)]  # 4 distinct days
        result = filter_contexts(contexts, start=date(2025, 3, 2), end=date(2025, 3, 3))

        self.assertEqual(len(result), 2)

    def test_limit_caps_result_count(self):
        result = filter_contexts(self.contexts, limit=2)

        self.assertEqual(len(result), 2)
        self.assertEqual(result, self.contexts[:2])

    def test_limit_larger_than_available_returns_all(self):
        result = filter_contexts(self.contexts, limit=100)

        self.assertEqual(result, self.contexts)

    def test_limit_applies_after_date_filtering(self):
        result = filter_contexts(self.contexts, start=date(2025, 3, 1), limit=1)

        self.assertEqual(result, self.contexts[:1])

    def test_empty_input_returns_empty_list(self):
        result = filter_contexts([], start=date(2025, 3, 1), end=date(2025, 3, 15), limit=10)

        self.assertEqual(result, [])

    def test_filters_can_produce_empty_result(self):
        result = filter_contexts(self.contexts, start=date(2030, 1, 1))

        self.assertEqual(result, [])


class DescribeEmptyResultTests(unittest.TestCase):
    def setUp(self):
        # 2025-03-01 00:00 .. 2025-03-01 04:00
        self.contexts = [_context(i) for i in range(5)]

    def test_no_dataset_at_all(self):
        message = describe_empty_result([], start=None, end=None)

        self.assertEqual(message, "No H1 MarketContexts are available in the loaded dataset.")

    def test_reports_dataset_available_range(self):
        message = describe_empty_result(self.contexts, start=date(2020, 1, 1), end=date(2020, 1, 15))

        self.assertIn("Dataset available range", message)
        self.assertIn("2025-03-01 00:00:00", message)
        self.assertIn("2025-03-01 04:00:00", message)

    def test_reports_requested_range(self):
        message = describe_empty_result(self.contexts, start=date(2020, 1, 1), end=date(2020, 1, 15))

        self.assertIn("Requested date range", message)
        self.assertIn("2020-01-01", message)
        self.assertIn("2020-01-15", message)

    def test_reports_unbounded_when_start_or_end_missing(self):
        message = describe_empty_result(self.contexts, start=None, end=None)

        self.assertIn("(unbounded)", message)

    def test_warns_when_start_is_after_dataset_end(self):
        message = describe_empty_result(self.contexts, start=date(2030, 1, 1), end=None)

        self.assertIn("falls entirely outside the available data", message)

    def test_warns_when_end_is_before_dataset_start(self):
        message = describe_empty_result(self.contexts, start=None, end=date(2020, 1, 1))

        self.assertIn("falls entirely outside the available data", message)

    def test_does_not_warn_about_range_when_range_overlaps_dataset(self):
        # Requested range overlaps the dataset - zero contexts here would
        # be caused by something else (e.g. --limit 0), not by the dates.
        message = describe_empty_result(self.contexts, start=date(2025, 3, 1), end=date(2025, 3, 1))

        self.assertNotIn("falls entirely outside", message)
        self.assertIn("check --limit", message)


class BuildDatasetSummaryTests(unittest.TestCase):
    def setUp(self):
        # 2025-03-01 00:00 .. 2025-03-01 04:00
        self.all_contexts = [_context(i) for i in range(5)]

    def test_reports_first_and_last_of_all_contexts_not_selected(self):
        selected = self.all_contexts[1:3]

        summary = build_dataset_summary(self.all_contexts, selected, start=None, end=None)

        self.assertEqual(summary.first_context_timestamp, self.all_contexts[0].timestamp)
        self.assertEqual(summary.last_context_timestamp, self.all_contexts[-1].timestamp)
        self.assertEqual(summary.contexts_available, 5)
        self.assertEqual(summary.contexts_selected, 2)

    def test_carries_requested_range_through_unchanged(self):
        summary = build_dataset_summary(
            self.all_contexts, self.all_contexts, start=date(2025, 3, 1), end=date(2025, 3, 15)
        )

        self.assertEqual(summary.requested_start, date(2025, 3, 1))
        self.assertEqual(summary.requested_end, date(2025, 3, 15))

    def test_empty_dataset_reports_none_timestamps_and_zero_counts(self):
        summary = build_dataset_summary([], [], start=None, end=None)

        self.assertIsNone(summary.first_context_timestamp)
        self.assertIsNone(summary.last_context_timestamp)
        self.assertEqual(summary.contexts_available, 0)
        self.assertEqual(summary.contexts_selected, 0)


if __name__ == "__main__":
    unittest.main()
