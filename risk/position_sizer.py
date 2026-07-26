"""Fixed-fractional position sizing: risk a constant % of equity per trade."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSizingResult:
    """Numeric breakdown of a single sizing calculation, for debugging."""

    risk_amount: float
    stop_loss_distance: float
    lot_size: float


class PositionSizer:
    """
    Converts a fixed risk percentage of account balance into a lot size,
    given the stop-loss distance for a specific trade.

    `value_per_price_unit_per_lot` is the only broker/instrument-specific
    input: how much account currency one lot gains or loses per 1.0 unit
    of price movement (e.g. derived from contract size). It is supplied
    by the caller, not looked up here, so this class has no dependency
    on any broker API and works the same in backtests and live trading.
    """

    def __init__(
        self,
        risk_per_trade_pct: float,
        value_per_price_unit_per_lot: float = 1.0,
    ):
        if not 0 < risk_per_trade_pct <= 1:
            raise ValueError("risk_per_trade_pct must be in (0, 1]")

        if value_per_price_unit_per_lot <= 0:
            raise ValueError("value_per_price_unit_per_lot must be positive")

        self.risk_per_trade_pct = risk_per_trade_pct
        self.value_per_price_unit_per_lot = value_per_price_unit_per_lot

    def calculate(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss_price: float,
    ) -> PositionSizingResult:
        """Return the lot size that risks `risk_per_trade_pct` of `account_balance`."""
        if account_balance <= 0:
            raise ValueError("account_balance must be positive")

        stop_loss_distance = abs(entry_price - stop_loss_price)
        if stop_loss_distance <= 0:
            raise ValueError("entry_price and stop_loss_price must differ")

        risk_amount = account_balance * self.risk_per_trade_pct
        lot_size = risk_amount / (stop_loss_distance * self.value_per_price_unit_per_lot)

        return PositionSizingResult(
            risk_amount=risk_amount,
            stop_loss_distance=stop_loss_distance,
            lot_size=lot_size,
        )
