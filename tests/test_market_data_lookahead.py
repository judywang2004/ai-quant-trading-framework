"""
Look-ahead regression tests for every multi-timeframe accessor on
MarketData, and for the H1 context builder that feeds the research
pipeline.

Rule under test: at time t, a candle is visible only if it has fully
closed (open timestamp + timeframe duration <= t).
"""

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from core.market_context import MarketContext
from core.market_data import MarketData
from core.timeframes import candle_close_time, timeframe_duration
from examples.demo_signal_engine import build_h1_contexts
from models.candle import Candle
from strategies.trend_pullback_strategy import TrendPullbackStrategy

START = datetime(2026, 1, 5)  # a Monday


def _candles(timeframe: str, count: int, start: datetime = START) -> list[Candle]:
    step = timeframe_duration(timeframe)
    return [
        Candle(
            symbol="TEST",
            timeframe=timeframe,
            timestamp=start + step * i,
            open=100.0 + i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.5 + i,
            volume=0.0,
        )
        for i in range(count)
    ]


def _market() -> MarketData:
    return MarketData(
        daily=_candles("D1", 10),
        h1=_candles("H1", 48),
        m15=_candles("M15", 96),
        m5=_candles("M5", 288),
    )


# (timeframe, MarketData attribute, history method, latest method)
ACCESSORS = [
    ("D1", "daily", "daily_history_until", "daily_at"),
    ("H1", "h1", "h1_history_until", "h1_at"),
    ("M15", "m15", "m15_history_until", "m15_at"),
    ("M5", "m5", "m5_history_until", "m5_at"),
]


class ClosedCandleAccessTests(unittest.TestCase):
    def setUp(self):
        self.market = _market()

    def test_history_excludes_candle_at_its_open_time(self):
        for timeframe, attr, history_method, _ in ACCESSORS:
            with self.subTest(timeframe=timeframe):
                candles = getattr(self.market, attr)
                target = candles[3]

                history = getattr(self.market, history_method)(target.timestamp)

                self.assertNotIn(target, history)
                self.assertEqual(history[-1], candles[2])

    def test_history_excludes_candle_one_second_before_close(self):
        for timeframe, attr, history_method, _ in ACCESSORS:
            with self.subTest(timeframe=timeframe):
                target = getattr(self.market, attr)[3]
                t = candle_close_time(target) - timedelta(seconds=1)

                self.assertNotIn(target, getattr(self.market, history_method)(t))

    def test_history_includes_candle_at_its_close_time(self):
        for timeframe, attr, history_method, _ in ACCESSORS:
            with self.subTest(timeframe=timeframe):
                target = getattr(self.market, attr)[3]

                history = getattr(self.market, history_method)(candle_close_time(target))

                self.assertEqual(history[-1], target)

    def test_lookback_counts_closed_candles_only(self):
        for timeframe, attr, history_method, _ in ACCESSORS:
            with self.subTest(timeframe=timeframe):
                candles = getattr(self.market, attr)
                t = candles[5].timestamp + timedelta(seconds=1)  # candle 5 forming

                history = getattr(self.market, history_method)(t, lookback=2)

                self.assertEqual(history, candles[3:5])

    def test_latest_candle_is_never_the_forming_one(self):
        for timeframe, attr, _, latest_method in ACCESSORS:
            with self.subTest(timeframe=timeframe):
                candles = getattr(self.market, attr)
                forming = candles[4]
                t = forming.timestamp + timeframe_duration(timeframe) / 2

                self.assertEqual(getattr(self.market, latest_method)(t), candles[3])
                self.assertEqual(
                    getattr(self.market, latest_method)(candle_close_time(forming)),
                    forming,
                )

    def test_nothing_is_visible_before_the_first_candle_closes(self):
        for timeframe, attr, history_method, latest_method in ACCESSORS:
            with self.subTest(timeframe=timeframe):
                first = getattr(self.market, attr)[0]

                self.assertEqual(getattr(self.market, history_method)(first.timestamp), [])
                self.assertIsNone(getattr(self.market, latest_method)(first.timestamp))

    def test_intraday_h1_never_sees_same_day_daily_candle(self):
        # 13:00 on day 3: day 3's D1 candle is still forming.
        t = START + timedelta(days=3, hours=13)

        self.assertEqual(self.market.daily_at(t), self.market.daily[2])
        self.assertEqual(self.market.daily_history_until(t)[-1], self.market.daily[2])


class ClockHandlingTests(unittest.TestCase):
    """MarketData compares candles and `t` on one clock, whatever it is."""

    def test_naive_server_clock_daily_candle_closes_at_next_midnight(self):
        # 2026-03-08 is a US DST change day. On a naive broker-server
        # clock every D1 candle still spans 00:00 -> 00:00 on that clock.
        day = datetime(2026, 3, 8)
        market = MarketData(daily=_candles("D1", 3, start=day - timedelta(days=1)), h1=[], m15=[], m5=[])

        self.assertEqual(market.daily_at(datetime(2026, 3, 8, 23, 59)).timestamp, day - timedelta(days=1))
        self.assertEqual(market.daily_at(datetime(2026, 3, 9)).timestamp, day)

    def test_utc_aware_candles_work(self):
        utc_start = START.replace(tzinfo=timezone.utc)
        market = MarketData(daily=[], h1=_candles("H1", 5, start=utc_start), m15=[], m5=[])

        t = utc_start + timedelta(hours=2, minutes=30)

        self.assertEqual(market.h1_at(t).timestamp, utc_start + timedelta(hours=1))

    def test_mixing_naive_and_aware_times_fails_loudly(self):
        market = _market()  # naive candles

        with self.assertRaises(TypeError):
            market.h1_history_until(START.replace(tzinfo=timezone.utc))


class H1ContextBuilderTimeSemanticsTests(unittest.TestCase):
    def test_context_distinguishes_bar_open_from_signal_availability(self):
        daily = _candles("D1", 60)
        market = MarketData(daily=daily, h1=_candles("H1", 60, start=daily[-3].timestamp), m15=[], m5=[])

        contexts = build_h1_contexts(market, TrendPullbackStrategy())

        self.assertTrue(contexts)
        for context in contexts:
            self.assertEqual(context.timestamp, context.bar_open_time)
            self.assertEqual(
                context.signal_available_time,
                context.bar_open_time + timedelta(hours=1),
            )

    def test_empty_context_has_no_times(self):
        context = MarketContext(symbol="TEST", timeframe="H1", timestamp=START, candles=())

        self.assertIsNone(context.bar_open_time)
        self.assertIsNone(context.signal_available_time)


class H1ContextBuilderLookaheadTests(unittest.TestCase):
    """The research pipeline's Daily Bias must not see the forming D1 candle."""

    def _market(self, daily: list[Candle]) -> MarketData:
        # 60 daily candles of history, then 3 days of H1 candles.
        h1_start = daily[-3].timestamp
        return MarketData(
            daily=daily,
            h1=_candles("H1", 72, start=h1_start),
            m15=[],
            m5=[],
        )

    def test_no_context_uses_a_daily_candle_that_closes_after_the_h1_close(self):
        daily = _candles("D1", 60)
        market = self._market(daily)

        contexts = build_h1_contexts(market, TrendPullbackStrategy())

        self.assertTrue(contexts)
        for context in contexts:
            decision_time = candle_close_time(context.latest_candle)
            used = context.daily_assessment.explanation.split("Date: ")[1][:10]
            used_day = next(c for c in daily if str(c.timestamp.date()) == used)
            self.assertLessEqual(candle_close_time(used_day), decision_time)

    def test_changing_todays_daily_close_does_not_change_intraday_contexts(self):
        daily = _candles("D1", 60)
        crashed_last_day = daily[:-1] + [replace(daily[-1], close=1.0, low=1.0)]

        normal = build_h1_contexts(self._market(daily), TrendPullbackStrategy())
        crashed = build_h1_contexts(self._market(crashed_last_day), TrendPullbackStrategy())

        last_day_close = candle_close_time(daily[-1])
        compared = 0
        for a, b in zip(normal, crashed):
            # While the last day is still forming, its close must be
            # invisible. (The 23:00 H1 candle closes exactly when the day
            # does, so from then on the day legitimately counts.)
            if candle_close_time(a.latest_candle) < last_day_close:
                self.assertEqual(a.daily_assessment, b.daily_assessment)
                compared += 1

        self.assertGreater(compared, 0)
        self.assertNotEqual(normal[-1].daily_assessment, crashed[-1].daily_assessment)


if __name__ == "__main__":
    unittest.main()
