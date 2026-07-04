"""Exponential moving average helpers."""

from typing import List, Sequence


def calculate_ema(closing_prices: Sequence[float], period: int = 10) -> List[float]:
    """Return the exponential moving average for each closing price.

    The implementation uses the standard EMA definition with a smoothing factor of
    ``2 / (period + 1)`` and initializes the first EMA value with the first price.

    Args:
        closing_prices: Sequence of closing prices to smooth.
        period: Number of periods used for the smoothing factor.

    Returns:
        A list containing the EMA values for each input price.
    """
    if not closing_prices:
        return []

    if period <= 0:
        raise ValueError("period must be greater than 0")

    alpha = 2.0 / (period + 1)
    emas: List[float] = []
    previous_ema: float | None = None

    for price in closing_prices:
        if previous_ema is None:
            previous_ema = float(price)
        else:
            previous_ema = float(price) * alpha + previous_ema * (1 - alpha)
        emas.append(previous_ema)

    return emas
