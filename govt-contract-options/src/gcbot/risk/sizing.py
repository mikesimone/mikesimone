"""Position sizing: largest whole contract count within the cap (DESIGN §7)."""

from __future__ import annotations

from decimal import ROUND_FLOOR, Decimal

from gcbot.config import RiskConfig

CONTRACT_MULTIPLIER = 100


def max_debit(buying_power: Decimal, risk: RiskConfig) -> Decimal:
    cap = buying_power * risk.max_pct_buying_power
    if risk.max_dollar_per_trade is not None:
        cap = min(cap, risk.max_dollar_per_trade)
    return cap


def contracts_for(premium: Decimal, buying_power: Decimal, risk: RiskConfig) -> int:
    """Return how many contracts to buy, or 0 if even one exceeds the cap."""
    if premium <= 0 or buying_power <= 0:
        return 0
    per_contract = premium * CONTRACT_MULTIPLIER
    qty = (max_debit(buying_power, risk) / per_contract).to_integral_value(rounding=ROUND_FLOOR)
    return int(qty)


def take_profit_price(entry: Decimal, risk: RiskConfig) -> Decimal:
    return (entry * (1 + risk.take_profit_pct)).quantize(Decimal("0.01"))
