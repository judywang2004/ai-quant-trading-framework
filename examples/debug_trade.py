from data.csv_loader import load_candles

candles = load_candles(
    "data/historical/USDJPY_M5.csv",
    symbol="USDJPY",
    timeframe="M5",
)

for candle in candles:
    if str(candle.timestamp) == "2026-04-19 23:20:00-04:00":
        print(candle)
        break