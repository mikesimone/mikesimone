import json
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from gcbot.sources.base import SourceError
from gcbot.sources.usaspending import SET_ASIDE_CODES, USASpendingSource

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text())


class FakePost:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __call__(self, url, body):
        self.calls.append(body)
        return self.pages[body["page"] - 1]


def test_request_shape():
    src = USASpendingSource(("SDVOSB",), D("1000000"), post=FakePost([]))
    body = src.build_request("SDVOSB", date(2026, 9, 22), date(2026, 9, 25), 1)
    f = body["filters"]
    assert f["award_type_codes"] == ["A", "B", "C", "D"]
    assert f["set_aside_type_codes"] == SET_ASIDE_CODES["SDVOSB"]
    assert f["time_period"][0] == {
        "start_date": "2026-09-22", "end_date": "2026-09-25", "date_type": "action_date",
    }
    assert f["award_amounts"] == [{"lower_bound": 1000000.0}]


def test_paginates_parses_and_filters():
    post = FakePost([load("usaspending_page1.json"), load("usaspending_page2.json")])
    src = USASpendingSource(("SBA",), D("1000000"), post=post)
    events = src.fetch_new_awards(date(2026, 9, 22), date(2026, 9, 25))

    assert [c["page"] for c in post.calls] == [1, 2]
    # Malformed row dropped; $900k row below threshold dropped.
    assert [e.award_id for e in events] == ["W912DY26C0001", "75N95026P0002"]
    top = events[0]
    assert top.recipient_name == "ACME DEFENSE SYSTEMS INC"
    assert top.amount == D("4500000.0")
    assert top.set_aside == "SBA"
    assert top.start_date == date(2026, 9, 22)
    assert events[1].recipient_uei is None


def test_same_award_under_two_set_asides_is_deduped():
    page = load("usaspending_page2.json")
    page["results"][0]["Award Amount"] = 2000000.0
    src = USASpendingSource(("SBA", "8a"), D("1000000"), post=lambda url, body: page)
    events = src.fetch_new_awards(date(2026, 9, 22), date(2026, 9, 25))
    assert len(events) == 1
    assert events[0].set_aside == "SBA"


def test_unknown_set_aside_rejected():
    with pytest.raises(ValueError):
        USASpendingSource(("NOPE",), D("1"))


def test_source_error_propagates():
    def boom(url, body):
        raise SourceError("down")

    src = USASpendingSource(("SBA",), D("1"), post=boom)
    with pytest.raises(SourceError):
        src.fetch_new_awards(date(2026, 9, 22), date(2026, 9, 25))
