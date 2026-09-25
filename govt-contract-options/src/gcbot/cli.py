"""Command-line entry point. One pass per invocation; systemd timers drive it."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta

from gcbot.config import Config, ConfigError, load_config
from gcbot.sources.base import AwardSource, SourceError
from gcbot.sources.usaspending import USASpendingSource
from gcbot.state.store import StateStore

log = logging.getLogger("gcbot")

IMPLEMENTED_SOURCES = {"usaspending"}


def build_sources(config: Config) -> list[tuple[AwardSource, int]]:
    """Return (source, lookback_days) for every enabled, implemented source."""
    out: list[tuple[AwardSource, int]] = []
    for name, sc in config.sources.items():
        if not sc.enabled:
            continue
        if name not in IMPLEMENTED_SOURCES:
            log.warning("source %s is enabled but not implemented yet; skipping", name)
            continue
        if name == "usaspending":
            src = USASpendingSource(config.signal.set_aside_types, config.signal.min_award_dollars)
            out.append((src, sc.lookback_days))
    return out


def cmd_check_config(config: Config) -> int:
    print(f"config OK: mode={config.mode} broker={config.broker}")
    return 0


def cmd_poll(config: Config, today: date) -> int:
    """Fetch awards, print the ones not seen before, and record them.

    dry_run records nothing, so repeated dry runs show the same awards.
    """
    persist = config.mode != "dry_run"
    store = StateStore(config.state_path if persist else ":memory:")
    failed = 0
    try:
        for source, lookback in build_sources(config):
            since = today - timedelta(days=lookback)
            try:
                events = source.fetch_new_awards(since, today)
            except SourceError as exc:
                log.error("%s: %s", source.name, exc)
                failed += 1
                continue
            new = [e for e in events if store.mark_seen(e)]
            log.info("%s: %d awards in window, %d new", source.name, len(events), len(new))
            for e in new:
                print(
                    f"{e.source}\t{e.award_id}\t{e.amount:,.0f}\t{e.set_aside}\t"
                    f"{e.recipient_name}\t{e.agency or ''}"
                )
    finally:
        store.close()
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gcbot")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check-config", help="validate the config file and exit")
    sub.add_parser("poll", help="fetch new awards and print them")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        config = load_config(args.config)
    except (ConfigError, OSError) as exc:
        log.error("refusing to start: %s", exc)
        return 2

    if args.command == "check-config":
        return cmd_check_config(config)
    if args.command == "poll":
        return cmd_poll(config, date.today())
    return 2


if __name__ == "__main__":
    sys.exit(main())
