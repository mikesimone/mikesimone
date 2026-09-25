"""Broker interface. Implementations: dryrun (here), schwab and alpaca (later)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from gcbot.models import AccountSnapshot, OrderPlan


class Broker(ABC):
    @abstractmethod
    def account_snapshot(self) -> AccountSnapshot:
        ...

    @abstractmethod
    def submit(self, plan: OrderPlan) -> str:
        """Submit an already gate-approved order. Returns an order reference."""
