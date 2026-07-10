import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from data.csv_loader import load_candles
from models.candle import Candle


class CsvLoaderTests(unittest.TestCase):
    def test_load_candles_reads_csv_and_parses_values(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
            handle.write(
                "symbol,timeframe,timestamp,open,high,low,close,volume\n"
                "AAPL,1m,2024-01-01T00:00:00,100.0,101.0,99.5,100.5,2500\n"
            )
            csv_path = Path(handle.name)

        try:
            candles = load_candles(csv_path, symbol="AAPL", timeframe="1m")

            self.assertEqual(len(candles), 1)
            candle = candles[0]
            self.assertIsInstance(candle, Candle)
            self.assertEqual(candle.symbol, "AAPL")
            self.assertEqual(candle.timeframe, "1m")
            self.assertEqual(candle.timestamp, datetime(2024, 1, 1, 0, 0, 0))
            self.assertEqual(candle.open, 100.0)
            self.assertEqual(candle.high, 101.0)
            self.assertEqual(candle.low, 99.5)
            self.assertEqual(candle.close, 100.5)
            self.assertEqual(candle.volume, 2500.0)
        finally:
            csv_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
