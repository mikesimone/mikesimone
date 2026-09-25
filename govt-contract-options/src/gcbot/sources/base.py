"""Common interface every award source implements (DESIGN §4)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from gcbot.models import AwardEvent


class SourceError(RuntimeError):
    """A source could not be read this cycle. The caller logs and skips."""


class AwardSource(ABC):
    name: str

    @abstractmethod
    def fetch_new_awards(self, since: date, until: date) -> list[AwardEvent]:
        """Return awards with activity in [since, until]. Dedup is the caller's job."""
