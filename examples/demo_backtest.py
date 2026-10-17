"""
Plumbing demo for Strategy -> Order -> Executor. NOT a realistic backtest.

SimulatedExecutor fills every order at the signal price and closes it at
take-profit instantly, so every trade is a winner and there are no
costs. Do not draw any conclusion about EMATrendStrategy from the
numbers this prints. Realistic simulation is Forex Research Track
Phase 1 (docs/forex/INTEGRATION_PLAN.md).
"""

from pathlib import Path

from core.market_data import MarketData
from data.csv_loader import load_candles
from data.yfinance_loader import load_yfinance

from execution.simulated_executor import SimulatedExecutor

from models.enums import OrderType
from models.order import Order

from risk.risk_manager import RiskManager

from strategies.ema_trend_strategy import EMATrendStrategy


CSV_FILE = Path("data/historical/USDJPY_M5.csv")


def main():

    if CSV_FILE.exists():

        print("Loading local historical data...")

        candles = load_candles(
            CSV_FILE,
            symbol="USDJPY",
            timeframe="M5",
        )

    else:

        print("Downloading historical data...")

        candles = load_yfinance(
            symbol="JPY=X",
            interval="5m",
            period="60d",
        )

    print(f"\nLoaded {len(candles)} candles.\n")

    # Strategy.generate_signal takes (MarketData, index into market.m5);
    # this demo only has M5 candles, so the other timeframes are empty.
    market = MarketData(daily=[], h1=[], m15=[], m5=candles)

    strategy = EMATrendStrategy()
    executor = SimulatedExecutor()
    risk_manager = RiskManager()

    trades = []
    last_signal = None

    for i in range(strategy.REQUIRED_HISTORY, len(candles)):

        history = candles[: i + 1]

        signal = strategy.generate_signal(market, i)

        if signal is None:
            continue

        # Prevent duplicate BUY/BUY/BUY...
        if signal.signal_type == last_signal:
            continue

        last_signal = signal.signal_type

        volume = risk_manager.calculate_volume()

        order = Order(
            signal=signal,
            order_type=OrderType.MARKET,
            volume=volume,
            price=signal.entry,
            timestamp=signal.timestamp,
        )

        trade = executor.execute(order)

        trades.append(trade)

        #
        # Debug first five trades
        #
        if len(trades) <= 5:

            current = history[-1]

            print("=" * 60)
            print(f"Trade #{len(trades)}")

            print(f"Time    : {current.timestamp}")
            print(f"Signal  : {signal.signal_type.name}")

            print(
                f"OHLC    : "
                f"O={current.open:.3f} "
                f"H={current.high:.3f} "
                f"L={current.low:.3f} "
                f"C={current.close:.3f}"
            )

            print(f"Entry   : {trade.entry_price:.3f}")
            print(f"Exit    : {trade.exit_price:.3f}")
            print(f"Profit  : {trade.profit:.3f}")

    #
    # Summary
    #
    total_profit = sum(t.profit for t in trades)

    wins = sum(1 for t in trades if t.profit > 0)
    losses = len(trades) - wins

    print("\n")
    print("=" * 60)
    print("Backtest Summary")
    print("=" * 60)

    print(f"Total Candles : {len(candles)}")
    print(f"Total Trades  : {len(trades)}")
    print(f"Wins          : {wins}")
    print(f"Losses        : {losses}")
    print(f"Net Profit    : {total_profit:.3f}")

    print("=" * 60)
    print("NOTE: not a realistic backtest - every trade exits at")
    print("take-profit with zero costs (see module docstring).")
    print("=" * 60)


if __name__ == "__main__":
    main()
