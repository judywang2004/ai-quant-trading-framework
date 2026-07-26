import unittest
from datetime import datetime, timedelta

from core.market_context import MarketContext
from core.opportunity import Opportunity, OpportunityType, PatternState
from models.candle import Candle
from models.market_bias import MarketBias
from models.trend_assessment import DailyTrendResult, TrendStrength
from patterns.detector import PatternDetector
from patterns.high_base_detector import HighBaseDetector

# Golden-path scenario, tuned to HighBaseDetector's default constants:
#   IMPULSE_LOOKBACK=5, IMPULSE_MIN_GAIN_PCT=0.01
#   BASE_LOOKBACK=10, MIN_BASE_CANDLES=5, MAX_BASE_RANGE_PCT=0.01
#   BREAKOUT_BUFFER_PCT=0.0
#
# Layout (16 candles total, oldest -> newest):
#   [0:5]   impulse leg   : closes 100.0 -> 102.0 (+2.0% gain, clears 1%)
#   [5:15]  base          : every candle high=102.9 low=102.0
#                           range_pct = 0.9/102.0 ~= 0.88% (clears < 1%)
#   [15]    breakout      : close=103.5, comfortably above base high 102.9

IMPULSE_CLOSES = [100.0, 100.5, 101.0, 101.5, 102.0]
BASE_HIGH = 102.9
BASE_LOW = 102.0
BASE_CLOSE = 102.4
BREAKOUT_CLOSE = 103.5


def _candle(index, open_, high, low, close) -> Candle:
    return Candle(
        symbol="USDJPY",
        timeframe="H1",
        timestamp=datetime(2024, 1, 1) + timedelta(hours=index),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=0.0,
    )


def _golden_candles(
    impulse_closes=IMPULSE_CLOSES,
    base_high=BASE_HIGH,
    base_low=BASE_LOW,
    breakout_close=BREAKOUT_CLOSE,
) -> tuple[Candle, ...]:
    candles = [
        _candle(i, c, c, c, c) for i, c in enumerate(impulse_closes)
    ]
    base_start = len(candles)
    for i in range(10):
        candles.append(
            _candle(base_start + i, BASE_CLOSE, base_high, base_low, BASE_CLOSE)
        )
    breakout_index = len(candles)
    candles.append(
        _candle(breakout_index, breakout_close, breakout_close + 0.1, breakout_close - 0.5, breakout_close)
    )
    return tuple(candles)


def _daily_assessment(strength=TrendStrength.STRONG, bias=MarketBias.BULLISH) -> DailyTrendResult:
    return DailyTrendResult(
        bias=bias,
        strength=strength,
        rules=(),
        ema20=154.23,
        ema50=153.10,
        ema20_slope=0.05,
        ema20_slope_status=None,
        ema_separation=1.13,
        ema_separation_pct=0.0074,
        explanation="test daily assessment",
    )


def _golden_context(**overrides) -> MarketContext:
    candles = overrides.pop("candles", None) or _golden_candles()
    defaults = dict(
        symbol="USDJPY",
        timeframe="H1",
        timestamp=candles[-1].timestamp,
        candles=candles,
        ema20=102.5,
        ema50=101.0,
        ema20_history=(101.0, 101.5, 102.0, 102.3, 102.5),
        daily_assessment=_daily_assessment(),
    )
    defaults.update(overrides)
    return MarketContext(**defaults)


class HighBaseDetectorGoldenPathTests(unittest.TestCase):
    def test_satisfies_pattern_detector_protocol_via_duck_typing(self):
        self.assertIsInstance(HighBaseDetector(), PatternDetector)

    def test_hb007_all_rules_pass_returns_opportunity(self):
        context = _golden_context()

        opportunity = HighBaseDetector().detect(context)

        self.assertIsInstance(opportunity, Opportunity)
        self.assertEqual(opportunity.symbol, context.symbol)
        self.assertEqual(opportunity.timeframe, context.timeframe)
        self.assertEqual(opportunity.timestamp, context.timestamp)
        self.assertEqual(opportunity.opportunity_type, OpportunityType.HIGH_BASE)
        self.assertEqual(opportunity.state, PatternState.READY)
        self.assertEqual(opportunity.bias, MarketBias.BULLISH)
        self.assertEqual(opportunity.entry_price, BREAKOUT_CLOSE)
        self.assertEqual(opportunity.stop_price, BASE_LOW)
        self.assertEqual(opportunity.confidence, 1.0)
        self.assertEqual(opportunity.quality, 5)
        self.assertEqual(opportunity.strategy_name, HighBaseDetector.NAME)

    def test_detect_returns_only_opportunity_or_none(self):
        detector = HighBaseDetector()

        passing = detector.detect(_golden_context())
        failing = detector.detect(_golden_context(daily_assessment=None))

        self.assertTrue(passing is None or isinstance(passing, Opportunity))
        self.assertTrue(failing is None or isinstance(failing, Opportunity))
        self.assertIsInstance(passing, Opportunity)
        self.assertIsNone(failing)


class HighBaseDetectorRuleTests(unittest.TestCase):
    def setUp(self):
        self.detector = HighBaseDetector()

    def test_hb001_rejects_when_daily_trend_is_not_strong(self):
        context = _golden_context(daily_assessment=_daily_assessment(strength=TrendStrength.WEAK))

        self.assertIsNone(self.detector.detect(context))

    def test_hb001_rejects_when_daily_assessment_missing(self):
        context = _golden_context(daily_assessment=None)

        self.assertIsNone(self.detector.detect(context))

    def test_hb002_rejects_when_ema20_not_above_ema50(self):
        context = _golden_context(ema20=100.0, ema50=101.0)

        self.assertIsNone(self.detector.detect(context))

    def test_hb003_rejects_when_ema20_is_falling(self):
        context = _golden_context(ema20_history=(102.5, 102.5, 102.0, 101.5, 101.0))

        self.assertIsNone(self.detector.detect(context))

    def test_hb003_rejects_with_fewer_than_two_ema20_history_points(self):
        context = _golden_context(ema20_history=(102.5,))

        self.assertIsNone(self.detector.detect(context))

    def test_hb004_rejects_when_impulse_leg_is_flat(self):
        flat_impulse = [100.0, 100.0, 100.0, 100.0, 100.0]
        context = _golden_context(candles=_golden_candles(impulse_closes=flat_impulse))

        self.assertIsNone(self.detector.detect(context))

    def test_hb005_rejects_when_base_range_too_wide(self):
        context = _golden_context(candles=_golden_candles(base_high=110.0))

        self.assertIsNone(self.detector.detect(context))

    def test_hb005_configurable_max_base_range_allows_wider_base(self):
        # base_high raised to 110.0 also requires raising breakout_close so
        # HB-006 (breakout above base high) still passes independently of
        # the HB-005 range check this test targets.
        wide_base_candles = _golden_candles(base_high=110.0, breakout_close=111.0)
        context = _golden_context(candles=wide_base_candles)

        strict_detector = HighBaseDetector()
        lenient_detector = HighBaseDetector(max_base_range_pct=0.10)

        self.assertIsNone(strict_detector.detect(context))
        self.assertIsInstance(lenient_detector.detect(context), Opportunity)

    def test_hb006_rejects_when_breakout_candle_does_not_close_above_base_high(self):
        context = _golden_context(candles=_golden_candles(breakout_close=102.5))

        self.assertIsNone(self.detector.detect(context))

    def test_hb006_breakout_buffer_is_configurable(self):
        # Breakout closes only marginally above the base high.
        marginal_candles = _golden_candles(breakout_close=BASE_HIGH + 0.01)
        context = _golden_context(candles=marginal_candles)

        lenient_detector = HighBaseDetector(breakout_buffer_pct=0.0)
        strict_detector = HighBaseDetector(breakout_buffer_pct=0.05)  # requires +5%

        self.assertIsInstance(lenient_detector.detect(context), Opportunity)
        self.assertIsNone(strict_detector.detect(context))

    def test_rejects_with_insufficient_candle_history(self):
        context = _golden_context(candles=_golden_candles()[-3:])

        self.assertIsNone(self.detector.detect(context))

    def test_constructor_rejects_invalid_min_base_candles(self):
        with self.assertRaises(ValueError):
            HighBaseDetector(base_lookback=10, min_base_candles=11)

    def test_constructor_rejects_invalid_lookbacks(self):
        with self.assertRaises(ValueError):
            HighBaseDetector(impulse_lookback=0)
        with self.assertRaises(ValueError):
            HighBaseDetector(base_lookback=0)


if __name__ == "__main__":
    unittest.main()
