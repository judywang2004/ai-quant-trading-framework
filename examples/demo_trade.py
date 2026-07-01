
from datetime import datetime
from execution.simulated_executor import SimulatedExecutor
from models.candle import Candle
from models.enums import OrderType
from models.order import Order
from risk.risk_manager import RiskManager
from strategies.dummy_strategy import DummyStrategy


def main():

    candle = Candle(
        symbol="USDJPY",
        timeframe="M5",
        timestamp=datetime.now(),

        open=145.200,
        high=145.260,
        low=145.180,
        close=145.230,

        volume=1000,
    )

    strategy = DummyStrategy()
    trade_signal = strategy.generate_signal(candle)

    risk_manager = RiskManager()
    volume = risk_manager.calculate_volume()

    order = Order(
        signal=trade_signal,
        order_type=OrderType.MARKET,
        volume=volume,
        price=trade_signal.entry,
        timestamp=candle.timestamp,
    )

    executor = SimulatedExecutor()
    trade = executor.execute(order)

    print("=" * 50)
    print("AI Quant Trading Platform")
    print("=" * 50)

    print(f"Strategy : {trade_signal.strategy_name}")
    print(f"Symbol   : {trade_signal.symbol}")
    print(f"Signal   : {trade_signal.signal_type.name}")

    print()

    print(f"Entry      : {trade_signal.entry:.3f}")
    print(f"Stop Loss  : {trade_signal.stop_loss:.3f}")
    print(f"Take Profit: {trade_signal.take_profit:.3f}")

    print()

    print(f"Exit        : {trade.exit_price:.3f}")
    print(f"Profit      : {trade.profit:.3f}")
    print(f"Status      : {trade.status.name}")

    print("=" * 50)


if __name__ == "__main__":
    main()