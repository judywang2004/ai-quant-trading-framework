import unittest

from indicators.ema import calculate_ema


class EmaIndicatorTests(unittest.TestCase):
    def test_calculate_ema_with_standard_formula(self):
        prices = [10.0, 11.0, 12.0, 13.0, 14.0]

        emas = calculate_ema(prices, period=2)

        self.assertEqual(len(emas), len(prices))
        self.assertEqual(emas[0], 10.0)
        self.assertAlmostEqual(emas[1], 10.666666666666666)
        self.assertAlmostEqual(emas[2], 11.555555555555555)
        self.assertAlmostEqual(emas[3], 12.518518518518519)
        self.assertAlmostEqual(emas[4], 13.506172839506172)

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(calculate_ema([], period=2), [])


if __name__ == "__main__":
    unittest.main()
