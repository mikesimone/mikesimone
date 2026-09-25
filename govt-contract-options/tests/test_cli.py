from dataclasses import replace
from datetime import date
from decimal import Decimal as D

from gcbot import cli
from gcbot.models import AwardEvent
from gcbot.sources.base import AwardSource, SourceError


class FakeSource(AwardSource):
    name = "fake"

    def __init__(self, events=None, error=False):
        self.events = events or []
        self.error = error

    def fetch_new_awards(self, since, until):
        if self.error:
            raise SourceError("down")
        return self.events


def ev(key):
    return AwardEvent("fake", key, key, "ACME", None, D("2000000"), "DoD", None, "SBA")


def test_poll_records_and_dedupes(tmp_path, config, monkeypatch, capsys):
    cfg = replace(config, state_path=str(tmp_path / "s.sqlite3"))
    monkeypatch.setattr(cli, "build_sources", lambda c: [(FakeSource([ev("A"), ev("B")]), 3)])
    assert cli.cmd_poll(cfg, date(2026, 9, 25)) == 0
    assert capsys.readouterr().out.count("\n") == 2
    assert cli.cmd_poll(cfg, date(2026, 9, 25)) == 0
    assert capsys.readouterr().out == ""


def test_dry_run_persists_nothing(tmp_path, config, monkeypatch):
    path = tmp_path / "s.sqlite3"
    cfg = replace(config, mode="dry_run", state_path=str(path))
    monkeypatch.setattr(cli, "build_sources", lambda c: [(FakeSource([ev("A")]), 3)])
    assert cli.cmd_poll(cfg, date(2026, 9, 25)) == 0
    assert not path.exists()


def test_source_failure_is_logged_not_fatal(tmp_path, config, monkeypatch, capsys):
    cfg = replace(config, state_path=str(tmp_path / "s.sqlite3"))
    monkeypatch.setattr(
        cli, "build_sources",
        lambda c: [(FakeSource(error=True), 3), (FakeSource([ev("A")]), 3)],
    )
    assert cli.cmd_poll(cfg, date(2026, 9, 25)) == 1
    assert "ACME" in capsys.readouterr().out


def test_check_config_cli(tmp_path):
    assert cli.main(["--config", "config.example.yaml", "check-config"]) == 0
    bad = tmp_path / "bad.yaml"
    bad.write_text("mode: live\n")
    assert cli.main(["--config", str(bad), "check-config"]) == 2
