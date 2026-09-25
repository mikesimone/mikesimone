"""Liquidity gate for a candidate contract (DESIGN §6). Pure; no I/O."""

from __future__ import annotations

from datetime import date

from gcbot.config import SelectionConfig, TradeabilityConfig
from gcbot.models import OptionQuote


def tradeability_failures(
    quote: OptionQuote,
    today: date,
    selection: SelectionConfig,
    rules: TradeabilityConfig,
) -> list[str]:
    """Return every reason the contract is untradeable. Empty list means pass."""
    failures: list[str] = []
    dte = (quote.expiry - today).days
    if dte < selection.min_days_to_expiry:
        failures.append(f"expiry {dte}d < min {selection.min_days_to_expiry}d")
    if dte > selection.max_days_to_expiry:
        failures.append(f"expiry {dte}d > max {selection.max_days_to_expiry}d")
    if quote.open_interest < rules.min_open_interest:
        failures.append(f"open interest {quote.open_interest} < {rules.min_open_interest}")
    if rules.require_nonzero_bid and quote.bid <= 0:
        failures.append("no bid")
    if quote.ask <= 0 or quote.ask < quote.bid:
        failures.append(f"bad quote bid={quote.bid} ask={quote.ask}")
    else:
        mid = (quote.bid + quote.ask) / 2
        spread_pct = (quote.ask - quote.bid) / mid
        if spread_pct > rules.max_spread_pct:
            failures.append(f"spread {spread_pct:.1%} > {rules.max_spread_pct:.1%}")
    return failures
