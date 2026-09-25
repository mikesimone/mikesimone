"""Risk gate: enforces invariants R1-R6 before any order leaves (DESIGN §2).

Pure function, no I/O. Any violation, or any input that cannot be verified,
blocks the order (fail closed).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from gcbot.config import Config
from gcbot.models import AccountSnapshot, OptionQuote, OrderPlan
from gcbot.resolve.tradeability import tradeability_failures
from gcbot.risk.sizing import max_debit, take_profit_price


@dataclass(frozen=True)
class GateResult:
    approved: bool
    violations: tuple[str, ...]


def check_order(
    plan: OrderPlan,
    quote: OptionQuote,
    account: AccountSnapshot,
    config: Config,
    today: date,
) -> GateResult:
    v: list[str] = []

    # R1: long calls only, buy-to-open.
    if plan.right != "CALL":
        v.append(f"R1: right must be CALL, got {plan.right}")
    if plan.side != "BUY_TO_OPEN":
        v.append(f"R1: side must be BUY_TO_OPEN, got {plan.side}")

    # R2: max loss = premium. Single positive-debit leg only.
    if plan.qty < 1:
        v.append(f"R2: qty must be >= 1, got {plan.qty}")
    if plan.limit_price <= 0:
        v.append(f"R2: limit price must be > 0, got {plan.limit_price}")

    # The plan must describe the contract we actually quoted.
    if (
        plan.option_symbol != quote.option_symbol
        or plan.underlying != quote.underlying
        or plan.expiry != quote.expiry
        or quote.right != "CALL"
    ):
        v.append("R1: plan does not match the quoted CALL contract")

    # R3: debit within the buying-power cap, against a live value.
    if account.buying_power is None or account.buying_power <= 0:
        v.append("R3: buying power unavailable; refusing to size against a stale value")
    elif plan.debit > max_debit(account.buying_power, config.risk):
        v.append(
            f"R3: debit {plan.debit} exceeds cap {max_debit(account.buying_power, config.risk)}"
        )

    # R4: take-profit exit must be set and consistent with config.
    if plan.limit_price > 0 and plan.take_profit_price != take_profit_price(
        plan.limit_price, config.risk
    ):
        v.append("R4: take-profit price does not match configured take_profit_pct")

    # R5 is structural: R1 + R3 mean every order is a cash debit within
    # available buying power, with no short leg that could create margin use.

    # R6: tradeable, liquid chain with a real exit.
    for reason in tradeability_failures(quote, today, config.selection, config.tradeability):
        v.append(f"R6: {reason}")

    # Runaway-loop caps (DESIGN §11 guardrails).
    if account.orders_today >= config.risk.max_orders_per_day:
        v.append(f"cap: {account.orders_today} orders today >= {config.risk.max_orders_per_day}")
    if account.open_positions >= config.risk.max_open_positions:
        v.append(
            f"cap: {account.open_positions} open positions >= {config.risk.max_open_positions}"
        )

    return GateResult(approved=not v, violations=tuple(v))
