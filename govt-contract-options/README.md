# gcbot

Watches public government contract awards to small businesses and trades
defined-risk long calls. See [DESIGN.md](DESIGN.md) for the full spec.

## Status

Built so far (DESIGN §13 steps 1, 2 partial, 4):

- Config loading with hard validation (refuses to start on out-of-bounds values).
- USASpending.gov award poller with SQLite dedup.
- Risk gate (R1–R6, daily/open-position caps) and 20%-of-buying-power sizing.
- Dry-run broker.

Not built yet: SAM / Defense.gov sources, name→ticker resolution, shadow
ledger, Schwab adapter, systemd units.

## Run (on Six)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
cp config.example.yaml config.yaml
gcbot --config config.yaml check-config
gcbot --config config.yaml poll       # prints new small-business awards >= $1M
pytest
```

`poll` records awards it has seen in `data/state.sqlite3`, so each run prints
only new ones. With `mode: dry_run` nothing is recorded.
