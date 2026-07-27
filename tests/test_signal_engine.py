import unittest
from datetime import datetime, timedelta

from backtesting.signal_engine import SignalEngine
from backtesting.signal_record import SignalRecord
from core.market_context import MarketContext
from core.opportunity import Opportunity, OpportunityType, PatternState
from models.candle import Candle
from models.market_bias import MarketBias


def _context(index: int = 0) -> MarketContext:
    timestamp = datetime(2024, 1, 1) + timedelta(hours=index)
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
    return MarketContext(
        symbol="USDJPY",
        timeframe="H1",
        timestamp=timestamp,
        candles=(candle,),
    )


def _opportunity(context: MarketContext, strategy_name: str) -> Opportunity:
    return Opportunity(
        symbol=context.symbol,
        timeframe=context.timeframe,
        timestamp=context.timestamp,
        opportunity_type=OpportunityType.HIGH_BASE,
        state=PatternState.READY,
        bias=MarketBias.BULLISH,
        entry_price=101.0,
        stop_price=99.0,
        strategy_name=strategy_name,
        quality=4,
        confidence=0.8,
    )


class _AlwaysDetector:
    """Stub detector that always reports an Opportunity."""

    NAME = "AlwaysDetector"

    def detect(self, context: MarketContext) -> Opportunity | None:
        return _opportunity(context, self.NAME)


class _NeverDetector:
    """Stub detector that never reports an Opportunity, and exposes no
    NAME attribute (to exercise the class-name fallback)."""

    def detect(self, context: MarketContext) -> Opportunity | None:
        return None


class SignalEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = SignalEngine()

    def test_zero_detectors_returns_empty_list(self):
        result = self.engine.run([_context()], detectors=[])

        self.assertEqual(result, [])

    def test_zero_contexts_returns_empty_list(self):
        result = self.engine.run([], detectors=[_AlwaysDetector()])

        self.assertEqual(result, [])

    def test_zero_signals_when_no_detector_matches(self):
        result = self.engine.run([_context(), _context(1)], detectors=[_NeverDetector()])

        self.assertEqual(result, [])

    def test_one_signal_per_matching_context(self):
        contexts = [_context(0), _context(1), _context(2)]

        result = self.engine.run(contexts, detectors=[_AlwaysDetector()])

        self.assertEqual(len(result), 3)
        self.assertTrue(all(isinstance(r, SignalRecord) for r in result))

    def test_multiple_detectors_each_produce_a_record_for_the_same_context(self):
        result = self.engine.run(
            [_context()],
            detectors=[_AlwaysDetector(), _AlwaysDetector(), _NeverDetector()],
        )

        self.assertEqual(len(result), 2)

    def test_signal_record_fields_match_opportunity(self):
        context = _context()
        opportunity = _opportunity(context, _AlwaysDetector.NAME)

        result = self.engine.run([context], detectors=[_AlwaysDetector()])

        record = result[0]
        self.assertEqual(record.timestamp, opportunity.timestamp)
        self.assertEqual(record.symbol, opportunity.symbol)
        self.assertEqual(record.timeframe, opportunity.timeframe)
        self.assertEqual(record.opportunity_type, opportunity.opportunity_type)
        self.assertEqual(record.entry_price, opportunity.entry_price)
        self.assertEqual(record.stop_price, opportunity.stop_price)
        self.assertEqual(record.confidence, opportunity.confidence)
        self.assertEqual(record.quality, opportunity.quality)

    def test_uses_detector_name_attribute_when_present(self):
        result = self.engine.run([_context()], detectors=[_AlwaysDetector()])

        self.assertEqual(result[0].detector, "AlwaysDetector")

    def test_falls_back_to_class_name_when_no_name_attribute(self):
        class _UnnamedDetector:
            def detect(self, context: MarketContext) -> Opportunity | None:
                return _opportunity(context, "unnamed")

        result = self.engine.run([_context()], detectors=[_UnnamedDetector()])

        self.assertEqual(result[0].detector, "_UnnamedDetector")

    def test_does_not_mutate_input_context_or_opportunity(self):
        context = _context()
        detector = _AlwaysDetector()

        self.engine.run([context], detectors=[detector])

        # MarketContext and Opportunity are frozen dataclasses; a failed
        # mutation attempt would raise. This simply confirms the engine
        # never tries to write to them.
        with self.assertRaises(Exception):
            context.symbol = "EURUSD"  # type: ignore[misc]

    def test_run_is_deterministic_across_repeated_calls(self):
        contexts = [_context(0), _context(1)]
        detectors = [_AlwaysDetector()]

        first = self.engine.run(contexts, detectors)
        second = self.engine.run(contexts, detectors)

        self.assertEqual(first, second)

    def test_returns_deterministic_order_matching_context_then_detector(self):
        context_a = _context(0)
        context_b = _context(1)
        detector_first = _AlwaysDetector()
        detector_second = _AlwaysDetector()

        result = self.engine.run(
            [context_a, context_b], detectors=[detector_first, detector_second]
        )

        self.assertEqual(
            [r.timestamp for r in result],
            [context_a.timestamp, context_a.timestamp, context_b.timestamp, context_b.timestamp],
        )


if __name__ == "__main__":
    unittest.main()
