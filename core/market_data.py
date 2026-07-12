from datetime import datetime

from models.candle import Candle


class MarketData:

    def __init__(
        self,
        daily: list[Candle],
        h1: list[Candle],
        m15: list[Candle],
        m5: list[Candle],
    ):
        self.daily = daily
        self.h1 = h1
        self.m15 = m15
        self.m5 = m5

    def __str__(self):

        return (
            f"MarketData("
            f"D1={len(self.daily)}, "
            f"H1={len(self.h1)}, "
            f"M15={len(self.m15)}, "
            f"M5={len(self.m5)})"
        )

    def daily_at(self, t: datetime) -> Candle | None:

        for candle in reversed(self.daily):

            if candle.timestamp.date() == t.date():
                return candle

        return None

    def h1_at(self, t: datetime) -> Candle | None:

        for candle in reversed(self.h1):

            if (
                candle.timestamp.year == t.year
                and candle.timestamp.month == t.month
                and candle.timestamp.day == t.day
                and candle.timestamp.hour == t.hour
            ):
                return candle

        return None

    def m15_at(self, t: datetime) -> Candle | None:

        minute = (t.minute // 15) * 15

        for candle in reversed(self.m15):

            if (
                candle.timestamp.year == t.year
                and candle.timestamp.month == t.month
                and candle.timestamp.day == t.day
                and candle.timestamp.hour == t.hour
                and candle.timestamp.minute == minute
            ):
                return candle

        return None