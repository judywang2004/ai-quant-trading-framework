import contextlib
import io
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from data.market_loader import load_market_data

REPO_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def _write_mt4_csv(path: Path, step: timedelta, count: int = 5) -> None:
    start = datetime(2026, 6, 1)
    rows = [
        f"{(start + step * i):%Y.%m.%d,%H:%M},1.1,1.2,1.0,1.1,100"
        for i in range(count)
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _load(data_dir, symbol="TEST"):
    with contextlib.redirect_stdout(io.StringIO()):
        return load_market_data(data_dir, symbol=symbol)


class LoadMarketDataTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        _write_mt4_csv(self.data_dir / "TEST_D1.csv", timedelta(days=1))
        _write_mt4_csv(self.data_dir / "TEST_H1.csv", timedelta(hours=1))
        _write_mt4_csv(self.data_dir / "TEST_M15.csv", timedelta(minutes=15))

    def tearDown(self):
        self._tmp.cleanup()

    def test_m5_is_optional(self):
        market = _load(self.data_dir)

        self.assertEqual(len(market.daily), 5)
        self.assertEqual(market.m5, [])

    def test_files_are_selected_by_symbol(self):
        market = _load(self.data_dir)

        self.assertEqual(market.h1[0].symbol, "TEST")
        with self.assertRaises(FileNotFoundError):
            _load(self.data_dir, symbol="EURUSD")

    def test_missing_required_timeframe_raises(self):
        (self.data_dir / "TEST_H1.csv").unlink()

        with self.assertRaises(FileNotFoundError):
            _load(self.data_dir)

    def test_mislabeled_timeframe_file_is_rejected(self):
        # Regression: USDJPY_M5.csv held M15 bars.
        _write_mt4_csv(self.data_dir / "TEST_M5.csv", timedelta(minutes=15))

        with self.assertRaisesRegex(ValueError, "does not match its timeframe label"):
            _load(self.data_dir)


class RepositoryDataTests(unittest.TestCase):
    @unittest.skipUnless((REPO_DATA_DIR / "USDJPY_D1.csv").exists(), "repo data not present")
    def test_bundled_usdjpy_data_matches_its_labels(self):
        market = _load(REPO_DATA_DIR, symbol="USDJPY")

        self.assertGreater(len(market.daily), 0)
        self.assertGreater(len(market.h1), 0)
        self.assertGreater(len(market.m15), 0)


if __name__ == "__main__":
    unittest.main()
