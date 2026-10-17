import unittest
from datetime import datetime, timedelta

from core.market_data import MarketData
from core.timeframes import candle_close_time
from indicators.ema import calculate_ema
from models.candle import Candle
from models.market_bias import MarketBias
from models.trend_assessment import SlopeStatus, TrendStrength
from strategies.daily_trend_assessment import DailyTrendAssessment


def _make_daily_market(closes, start=datetime(2024, 1, 1)):
    candles = [
        Candle(
            symbol="TEST",
            timeframe="D1",
            timestamp=start + timedelta(days=i),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=0.0,
        )
        for i, close in enumerate(closes)
    ]
    return MarketData(daily=candles, h1=[], m15=[], m5=[])


def _last_close_time(market):
    """Decision time at which every daily candle in `market` has closed."""
    return candle_close_time(market.daily[-1])


class DailyTrendAssessmentTests(unittest.TestCase):
    # ------------------------------------------------------------------
    # Insufficient history
    # ------------------------------------------------------------------

    def test_insufficient_history_returns_neutral_and_no_strength(self):
        closes = [float(i) for i in range(1, 10)]  # only 9 candles
        market = _make_daily_market(closes)
        assessment = DailyTrendAssessment()

        result = assessment.assess(market, _last_close_time(market))

        self.assertEqual(result.bias, MarketBias.NEUTRAL)
        self.assertEqual(result.strength, TrendStrength.NONE)
        self.assertIsNone(result.ema20)
        self.assertIsNone(result.ema50)
        self.assertIsNone(result.ema20_slope_status)
        self.assertIsNone(result.ema_separation_pct)
        self.assertIn("Insufficient daily history", result.explanation)

    # ------------------------------------------------------------------
    # Rule 1: EMA Alignment
    # ------------------------------------------------------------------

    def test_downtrend_fails_alignment_and_returns_neutral(self):
        closes = [float(100 - i) for i in range(80)]  # strictly decreasing
        market = _make_daily_market(closes)
        assessment = DailyTrendAssessment()

        result = assessment.assess(market, _last_close_time(market))

        self.assertEqual(result.bias, MarketBias.NEUTRAL)
        self.assertEqual(result.strength, TrendStrength.NONE)
        alignment = result.rule(DailyTrendAssessment.RULE_EMA_ALIGNMENT)
        self.assertFalse(alignment.passed)

    # ------------------------------------------------------------------
    # Strong bullish trend
    # ------------------------------------------------------------------

    def test_steady_uptrend_is_bullish_and_strong(self):
        closes = [float(i) for i in range(1, 101)]  # strictly increasing
        market = _make_daily_market(closes)
        assessment = DailyTrendAssessment()  # default thresholds: 0.0

        result = assessment.assess(market, _last_close_time(market))

        self.assertEqual(result.bias, MarketBias.BULLISH)
        self.assertEqual(result.strength, TrendStrength.STRONG)
        self.assertGreater(result.ema20, result.ema50)
        self.assertEqual(result.ema20_slope_status, SlopeStatus.RISING)
        for rule in result.rules:
            if rule.name == DailyTrendAssessment.RULE_MARKET_STRUCTURE:
                continue
            self.assertTrue(rule.passed, rule.detail)

    # ------------------------------------------------------------------
    # Rule 3: EMA Separation (weak trend + configurable threshold)
    # ------------------------------------------------------------------

    def test_uptrend_becomes_weak_when_separation_threshold_too_high(self):
        closes = [float(i) for i in range(1, 101)]
        market = _make_daily_market(closes)
        assessment = DailyTrendAssessment(min_ema_separation_pct=1.0)  # 100%, unreachable

        result = assessment.assess(market, _last_close_time(market))

        self.assertEqual(result.bias, MarketBias.BULLISH)
        self.assertEqual(result.strength, TrendStrength.WEAK)
        separation_rule = result.rule(DailyTrendAssessment.RULE_EMA_SEPARATION)
        self.assertFalse(separation_rule.passed)
        # alignment and slope still hold - only separation is the blocker.
        self.assertTrue(result.rule(DailyTrendAssessment.RULE_EMA_ALIGNMENT).passed)
        self.assertTrue(result.rule(DailyTrendAssessment.RULE_EMA_SLOPE).passed)

    def test_separation_threshold_is_configurable(self):
        closes = [float(i) for i in range(1, 101)]
        market = _make_daily_market(closes)

        lenient = DailyTrendAssessment(min_ema_separation_pct=0.0)
        strict = DailyTrendAssessment(min_ema_separation_pct=1.0)

        lenient_result = lenient.assess(market, _last_close_time(market))
        strict_result = strict.assess(market, _last_close_time(market))

        self.assertEqual(lenient_result.strength, TrendStrength.STRONG)
        self.assertEqual(strict_result.strength, TrendStrength.WEAK)
        # Raw separation is identical - only the pass/fail threshold changed.
        self.assertEqual(lenient_result.ema_separation, strict_result.ema_separation)

    # ------------------------------------------------------------------
    # Rule 2: EMA20 Rising / Flat / Falling
    # ------------------------------------------------------------------

    def test_flat_ema20_is_weak_not_none(self):
        rising = [float(i) for i in range(1, 91)]
        # Tiny increments: technically rising, but negligible relative to price.
        flat_tail = [rising[-1] + i * 0.001 for i in range(1, 11)]
        closes = rising + flat_tail
        market = _make_daily_market(closes)

        # Confirm, independently, that the raw slope is positive but tiny.
        ema20 = calculate_ema(closes, DailyTrendAssessment().fast_period)
        lookback = DailyTrendAssessment().slope_lookback
        raw_slope = (ema20[-1] - ema20[-lookback]) / (lookback - 1)
        raw_slope_pct = raw_slope / ema20[-1]
        self.assertGreater(raw_slope_pct, 0)

        # A flat-slope threshold comfortably above that tiny value should
        # classify it as FLAT rather than RISING.
        assessment = DailyTrendAssessment(
            flat_slope_threshold_pct=raw_slope_pct * 10
        )
        result = assessment.assess(market, _last_close_time(market))

        self.assertEqual(result.ema20_slope_status, SlopeStatus.FLAT)
        self.assertEqual(result.bias, MarketBias.BULLISH)
        self.assertEqual(result.strength, TrendStrength.WEAK)
        slope_rule = result.rule(DailyTrendAssessment.RULE_EMA_SLOPE)
        self.assertFalse(slope_rule.passed)

    def test_falling_ema20_overrides_alignment_and_returns_none(self):
        rising = [float(i) for i in range(1, 91)]
        declining = [rising[-1] - i * 2.0 for i in range(1, 11)]
        closes = rising + declining
        market = _make_daily_market(closes)
        assessment = DailyTrendAssessment()

        # Independently confirm, using the same EMA function, that the
        # tail of this series produces a negative EMA20 slope while
        # EMA20 is still above EMA50 (alignment alone would say bullish).
        ema20 = calculate_ema(closes, assessment.fast_period)
        ema50 = calculate_ema(closes, assessment.slow_period)
        expected_slope = (ema20[-1] - ema20[-assessment.slope_lookback]) / (
            assessment.slope_lookback - 1
        )
        self.assertLess(expected_slope, 0)
        self.assertGreater(ema20[-1], ema50[-1])

        result = assessment.assess(market, _last_close_time(market))

        self.assertEqual(result.ema20_slope_status, SlopeStatus.FALLING)
        self.assertTrue(result.rule(DailyTrendAssessment.RULE_EMA_ALIGNMENT).passed)
        # Falling EMA20 overrides a passing alignment rule.
        self.assertEqual(result.bias, MarketBias.NEUTRAL)
        self.assertEqual(result.strength, TrendStrength.NONE)

    # ------------------------------------------------------------------
    # Rule 4: Market Structure placeholder
    # ------------------------------------------------------------------

    def test_market_structure_rule_is_not_implemented_placeholder(self):
        closes = [float(i) for i in range(1, 101)]
        market = _make_daily_market(closes)
        assessment = DailyTrendAssessment()

        result = assessment.assess(market, _last_close_time(market))

        rule = result.rule(DailyTrendAssessment.RULE_MARKET_STRUCTURE)
        self.assertIsNone(rule.passed)
        self.assertIn("not implemented", rule.detail.lower())
        # Still STRONG - the placeholder must not affect classification.
        self.assertEqual(result.strength, TrendStrength.STRONG)

    # ------------------------------------------------------------------
    # Completed-candle / configuration behaviour
    # ------------------------------------------------------------------

    def test_only_completed_candles_up_to_current_time_are_used(self):
        closes = [float(i) for i in range(1, 101)]
        market = _make_daily_market(closes)
        assessment = DailyTrendAssessment()

        cutoff_index = 69  # exclude the last 30 candles
        cutoff_time = candle_close_time(market.daily[cutoff_index])

        truncated_market = _make_daily_market(closes[: cutoff_index + 1])

        result = assessment.assess(market, cutoff_time)
        expected = assessment.assess(
            truncated_market, _last_close_time(truncated_market)
        )

        self.assertEqual(result.ema20, expected.ema20)
        self.assertEqual(result.ema50, expected.ema50)
        self.assertEqual(result.ema20_slope, expected.ema20_slope)
        self.assertEqual(result.ema20_slope_status, expected.ema20_slope_status)

    def test_intraday_assessment_ignores_the_still_forming_daily_candle(self):
        # Regression: at any time during day D, day D's candle has not
        # closed, so its close must not influence the assessment.
        closes = [float(i) for i in range(1, 101)]
        crashed = closes[:-1] + [1.0]  # same history, last day crashes

        assessment = DailyTrendAssessment()
        intraday = _make_daily_market(closes).daily[-1].timestamp + timedelta(hours=13)

        normal = assessment.assess(_make_daily_market(closes), intraday)
        with_crash = assessment.assess(_make_daily_market(crashed), intraday)

        self.assertEqual(normal.ema20, with_crash.ema20)
        self.assertEqual(normal.ema50, with_crash.ema50)
        self.assertEqual(normal.strength, with_crash.strength)
        self.assertIn("Date: 2024-04-08", normal.explanation)  # day 99, not 100

    def test_daily_candle_counts_once_it_has_closed(self):
        closes = [float(i) for i in range(1, 101)]
        market = _make_daily_market(closes)
        assessment = DailyTrendAssessment()

        just_before_close = _last_close_time(market) - timedelta(seconds=1)

        before = assessment.assess(market, just_before_close)
        at_close = assessment.assess(market, _last_close_time(market))

        self.assertNotEqual(before.ema20, at_close.ema20)
        self.assertIn("Date: 2024-04-09", at_close.explanation)  # day 100

    def test_slope_lookback_is_configurable(self):
        closes = [float(i) for i in range(1, 101)]
        market = _make_daily_market(closes)

        short_lookback = DailyTrendAssessment(slope_lookback=3)
        long_lookback = DailyTrendAssessment(slope_lookback=20)

        short_result = short_lookback.assess(market, _last_close_time(market))
        long_result = long_lookback.assess(market, _last_close_time(market))

        self.assertNotEqual(short_result.ema20_slope, long_result.ema20_slope)

    def test_invalid_slope_lookback_raises(self):
        with self.assertRaises(ValueError):
            DailyTrendAssessment(slope_lookback=1)


if __name__ == "__main__":
    unittest.main()
