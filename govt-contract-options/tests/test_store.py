from datetime import date
from decimal import Decimal as D

from gcbot.models import AwardEvent
from gcbot.state.store import StateStore


def event(key="K1"):
    return AwardEvent("usaspending", key, "PIID", "ACME", None, D("1000000"), None,
                      date(2026, 9, 25), "SBA")


def test_mark_seen_is_idempotent(tmp_path):
    store = StateStore(tmp_path / "state.sqlite3")
    assert store.mark_seen(event()) is True
    assert store.mark_seen(event()) is False
    assert store.is_seen(event())
    assert not store.is_seen(event("K2"))
    store.close()


def test_survives_restart(tmp_path):
    path = tmp_path / "state.sqlite3"
    StateStore(path).mark_seen(event())
    assert StateStore(path).is_seen(event())
