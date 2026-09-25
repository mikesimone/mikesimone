"""Plain data carriers passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class AwardEvent:
    """One contract award as reported by a source."""

    source: str
    award_key: str          # stable dedup key, unique per source
    award_id: str           # PIID or equivalent human-facing ID
    recipient_name: str
    recipient_uei: str | None
    amount: Decimal
    agency: str | None
    start_date: date | None
    set_aside: str | None


@dataclass(frozen=True)
class OptionQuote:
    """Read-only snapshot of one option contract."""

    option_symbol: str
    underlying: str
    right: str              # "CALL" | "PUT"
    strike: Decimal
    expiry: date
    bid: Decimal
    ask: Decimal
    open_interest: int


@dataclass(frozen=True)
class OrderPlan:
    """A single-leg order the risk gate will approve or reject.

    Deliberately single-leg: there is no way to express a spread or a short
    leg with this type (R2).
    """

    award_key: str
    underlying: str
    option_symbol: str
    right: str              # must be "CALL" (R1)
    side: str               # must be "BUY_TO_OPEN" (R1)
    qty: int
    limit_price: Decimal    # per-share premium
    expiry: date
    take_profit_price: Decimal

    @property
    def debit(self) -> Decimal:
        return self.limit_price * self.qty * 100


@dataclass(frozen=True)
class AccountSnapshot:
    """What the gate needs to know about the account at submit time.

    buying_power is None when the live fetch failed; the gate treats that as
    a hard block rather than sizing against a stale value (DESIGN §11).
    """

    buying_power: Decimal | None
    orders_today: int
    open_positions: int
