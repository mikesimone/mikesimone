"""Dry-run broker: logs the order it would place and places nothing."""

from __future__ import annotations

import logging
from decimal import Decimal

from gcbot.broker.base import Broker
from gcbot.models import AccountSnapshot, OrderPlan

log = logging.getLogger(__name__)


class DryRunBroker(Broker):
    def __init__(self, buying_power: Decimal):
        self._buying_power = buying_power
        self.submitted: list[OrderPlan] = []

    def account_snapshot(self) -> AccountSnapshot:
        return AccountSnapshot(
            buying_power=self._buying_power,
            orders_today=len(self.submitted),
            open_positions=len(self.submitted),
        )

    def submit(self, plan: OrderPlan) -> str:
        self.submitted.append(plan)
        log.info(
            "DRY RUN: would BUY_TO_OPEN %d x %s @ %s (debit %s, take-profit %s)",
            plan.qty, plan.option_symbol, plan.limit_price, plan.debit, plan.take_profit_price,
        )
        return f"dryrun-{len(self.submitted)}"
