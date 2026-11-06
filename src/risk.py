"""Educational position sizing helper. It does not place trades."""


def calculate_position_size(
    account_balance: float,
    risk_percent: float,
    stop_distance_price: float,
    value_per_price_unit_per_lot: float,
) -> float:
    """Estimate lots from stop distance and cash risk; broker contract specs vary.

    value_per_price_unit_per_lot must be obtained from the broker's symbol contract
    specifications. This helper intentionally does not guess pip or tick values.
    """
    if account_balance <= 0:
        raise ValueError("Account balance must be positive.")
    if not 0 < risk_percent <= 1:
        raise ValueError("risk_percent must be greater than 0 and at most 1.")
    if stop_distance_price <= 0 or value_per_price_unit_per_lot <= 0:
        raise ValueError("Stop distance and value per price unit must be positive.")

    cash_risk = account_balance * (risk_percent / 100)
    lots = cash_risk / (stop_distance_price * value_per_price_unit_per_lot)
    return lots
