"""USASpending.gov adapter (official REST API, no key).

Uses POST /api/v2/search/spending_by_award/ filtered to contract award types,
the configured small-business set-asides, a minimum award amount, and an
action-date window. One query per set-aside group so each event carries the
set-aside that matched it.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

import requests

from gcbot.models import AwardEvent
from gcbot.sources.base import AwardSource, SourceError

API_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

# Contract award types: BPA call, purchase order, delivery order, definitive contract.
CONTRACT_AWARD_TYPES = ["A", "B", "C", "D"]

# Config-friendly names -> FPDS type_set_aside codes.
SET_ASIDE_CODES: dict[str, list[str]] = {
    "8a": ["8A", "8AN"],
    "WOSB": ["WOSB", "WOSBSS", "EDWOSB", "EDWOSBSS"],
    "SDVOSB": ["SDVOSBC", "SDVOSBS"],
    "HUBZone": ["HZC", "HZS"],
    "SBA": ["SBA", "SBP"],
}

FIELDS = [
    "Award ID",
    "Recipient Name",
    "Recipient UEI",
    "Award Amount",
    "Awarding Agency",
    "Start Date",
    "generated_internal_id",
]

PAGE_SIZE = 100
MAX_PAGES = 20  # hard stop so a bad cursor can't loop forever

PostFn = Callable[[str, dict[str, Any]], dict[str, Any]]


def _default_post(url: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        resp = requests.post(url, json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise SourceError(f"usaspending request failed: {exc}") from exc


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def parse_row(row: dict[str, Any], set_aside: str) -> AwardEvent | None:
    """Turn one API result row into an AwardEvent. Malformed rows return None."""
    key = row.get("generated_internal_id")
    name = row.get("Recipient Name")
    try:
        amount = Decimal(str(row.get("Award Amount")))
    except (InvalidOperation, TypeError):
        return None
    if not key or not name:
        return None
    return AwardEvent(
        source="usaspending",
        award_key=str(key),
        award_id=str(row.get("Award ID") or key),
        recipient_name=str(name).strip(),
        recipient_uei=row.get("Recipient UEI") or None,
        amount=amount,
        agency=row.get("Awarding Agency") or None,
        start_date=_parse_date(row.get("Start Date")),
        set_aside=set_aside,
    )


class USASpendingSource(AwardSource):
    name = "usaspending"

    def __init__(
        self,
        set_aside_types: tuple[str, ...],
        min_award_dollars: Decimal,
        post: PostFn = _default_post,
    ):
        unknown = [t for t in set_aside_types if t not in SET_ASIDE_CODES]
        if unknown:
            raise ValueError(f"unknown set-aside types: {unknown}")
        self.set_aside_types = set_aside_types
        self.min_award_dollars = min_award_dollars
        self._post = post

    def build_request(self, set_aside: str, since: date, until: date, page: int) -> dict[str, Any]:
        return {
            "filters": {
                "award_type_codes": CONTRACT_AWARD_TYPES,
                "set_aside_type_codes": SET_ASIDE_CODES[set_aside],
                "time_period": [
                    {
                        "start_date": since.isoformat(),
                        "end_date": until.isoformat(),
                        "date_type": "action_date",
                    }
                ],
                "award_amounts": [{"lower_bound": float(self.min_award_dollars)}],
            },
            "fields": FIELDS,
            "limit": PAGE_SIZE,
            "page": page,
            "sort": "Award Amount",
            "order": "desc",
        }

    def fetch_new_awards(self, since: date, until: date) -> list[AwardEvent]:
        events: dict[str, AwardEvent] = {}
        for set_aside in self.set_aside_types:
            for page in range(1, MAX_PAGES + 1):
                data = self._post(API_URL, self.build_request(set_aside, since, until, page))
                for row in data.get("results") or []:
                    event = parse_row(row, set_aside)
                    if event is not None and event.amount >= self.min_award_dollars:
                        events.setdefault(event.award_key, event)
                if not (data.get("page_metadata") or {}).get("hasNext"):
                    break
        return sorted(events.values(), key=lambda e: e.amount, reverse=True)
