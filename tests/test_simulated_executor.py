import unittest
from datetime import datetime

from execution.simulated_executor import SimulatedExecutor
from models.enums import OrderStatus, OrderType, SignalType, TradeStatus
from models.order import Order
from models.signal import Signal


class SimulatedExecutorTests(unittest.TestCase):
    def _make_order(self, signal_type, entry, take_profit):
        signal = Signal(
            symbol="AAPL",
            timeframe="1m",
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
            signal_type=signal_type,
            strategy_name="test",
            entry=entry,
            stop_loss=10.0,
            take_profit=take_profit,
            confidence=1.0,
        )
        return Order(
            signal=signal,
            order_type=OrderType.MARKET,
            volume=2.0,
            price=entry,
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
        )

    def test_buy_order_exits_at_take_profit(self):
        executor = SimulatedExecutor()
        order = self._make_order(SignalType.BUY, 100.0, 110.0)

        trade = executor.execute(order)

        self.assertEqual(order.status, OrderStatus.FILLED)
        self.assertEqual(trade.entry_price, 100.0)
        self.assertEqual(trade.exit_price, 110.0)
        self.assertEqual(trade.status, TradeStatus.CLOSED)
        self.assertAlmostEqual(trade.profit, 20.0)

    def test_sell_order_exits_at_take_profit(self):
        executor = SimulatedExecutor()
        order = self._make_order(SignalType.SELL, 110.0, 100.0)

        trade = executor.execute(order)

        self.assertEqual(order.status, OrderStatus.FILLED)
        self.assertEqual(trade.entry_price, 110.0)
        self.assertEqual(trade.exit_price, 100.0)
        self.assertEqual(trade.status, TradeStatus.CLOSED)
        self.assertAlmostEqual(trade.profit, 20.0)


if __name__ == "__main__":
    unittest.main()
