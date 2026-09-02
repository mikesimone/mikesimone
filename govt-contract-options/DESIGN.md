# Government Contract Options Bot — Design Document

**Status:** Draft (design phase — no trading code yet)
**Author:** Design pass for the automated contract-award options watcher
**Stack:** Python 3.11+, Alpaca (paper first), official government data APIs

---

## 1. What this is

An automated tool that:

1. Watches public government contract-award data for new awards to **small
   businesses**.
2. Maps each awardee to a **publicly traded ticker** (dropping private
   companies and anything without a tradeable options chain).
3. When an award clears a configurable threshold, buys **long call options**
   in that company.
4. Automatically sells each position at a configurable **profit target** and
   otherwise lets it **expire worthless**.

### Why this is legitimate

Government contract awards are **public information** — USASpending.gov,
SAM.gov, and FPDS exist specifically to publish them. Trading on public data
is not insider trading. This is a personal, defined-risk trading tool.

### Non-goals (v1)

- No short options, spreads, or any position with undefined/unlimited risk.
- No margin, no naked positions, no assignment exposure.
- No day-trading / high-frequency behavior. This is event-driven, low-cadence.
- No guarantee of profitability. This is a signal-execution harness, not alpha.

---

## 2. Core risk invariants (hard rules, enforced in code)

These are the constraints from the project owner, restated as invariants the
risk gate **must** enforce before any order is submitted. A violation is a
hard block, not a warning.

| # | Invariant | Rationale |
|---|-----------|-----------|
| R1 | **Long calls only** (buy-to-open, debit paid up front). | Max loss = premium. You can never owe money or be assigned. Satisfies "no order leaves me on the hook." |
| R2 | **Max loss per position = premium paid.** No short legs, ever. | A losing trade simply expires worthless. |
| R3 | **No single order > 20% of available buying power** at submit time. | Position sizing cap from owner. Evaluated against *live* buying power, not a cached value. |
| R4 | **Take-profit auto-sell** at `+N%` unrealized gain (default +50%). | Locks in wins without manual watching. |
| R5 | **No margin, no options level above the long-call tier.** | Keeps account in defined-risk territory structurally, not just by convention. |
| R6 | **Skip untradeable / illiquid chains.** | Enforces that we only trade where a real exit exists. See §6. |

If any invariant cannot be verified for a candidate order, the default action
is **do nothing** (fail closed).

---

## 3. Broker choice: Alpaca

**Decision: Alpaca, paper-trading first, live later via config swap.**

Rationale:

- **Official, supported API with real API keys** — we are not impersonating a
  mobile app.
- Real SEC-registered / FINRA-member broker-dealer: paper and live are the
  same API, differing only by base URL + keys.
- First-class `alpaca-py` SDK, options trading support, free paper environment
  with real market data.

### Why not Robinhood

Robinhood has **no official public trading API**. The only access is
unofficial reverse-engineered libraries hitting its private mobile endpoints,
which:

- Violate Robinhood's Terms of Service.
- Break without notice when endpoints change.
- Risk account flagging/lockout.

That path is explicitly rejected for this build.

### Account prerequisites (manual, one-time)

- Alpaca account created.
- **Options trading approval** enabled (long-call tier is the lowest level;
  required even in paper). Orders will reject until this is granted.
- API key + secret for paper; separate key/secret for live.

---

## 4. Data sources

All official APIs where possible; scrape only where no feed exists.

| Source | Access | Role | Notes |
|--------|--------|------|-------|
| **USASpending.gov** | Official REST API, no key | Backbone. All federal award actions, filterable by set-aside type (8(a), WOSB, SDVOSB, HUBZone). | Most small-business signal comes from here. |
| **SAM.gov** | Official REST API, free key | Contract opportunities + awards. | Requires registering for an API key. |
| **FPDS** | ATOM/API feed | Raw contract-action feed underlying USASpending; sometimes fresher. | Secondary confirmation / earlier notice. |
| **Defense.gov contract announcements** | HTML page, scrape | DoD posts daily awards > $7.5M; often the *earliest* public notice for defense names. | Stable page, simple parse. Only non-API source in v1. |
| **Grants.gov** *(optional)* | Official API | Grant awards. | Weaker equity signal than procurement; behind a config flag, default off. |

### Polling model

- Poll each source on an interval (default: every 30 min during market days;
  configurable per source).
- Deduplicate by a stable award key (award ID / PIID + action date) persisted
  in local state so an award is never acted on twice.
- Each source is a **pluggable adapter** implementing a common
  `fetch_new_awards(since) -> list[AwardEvent]` interface.

---

## 5. Awardee → ticker mapping (the hard part)

Most awardees are **private companies or micro-caps with no listed options**.
This stage is where most award events are correctly discarded.

Pipeline per awardee:

1. **Normalize** the legal entity name (strip "LLC", "Inc.", DBA aliases).
2. **Resolve to a ticker** via a symbol-lookup source (e.g. an equities
   reference dataset or the broker's asset endpoint). Cache results; maintain a
   manual override map for known tricky names.
3. **Public-company filter** — if no ticker resolves with confidence, drop.
4. **Options-listed filter** — confirm the underlying has a listed options
   chain via the broker.
5. **Liquidity filter** — see §6.

A low-confidence match is treated as **no match** (fail closed). We would
rather miss a trade than trade the wrong company.

---

## 6. Tradeability / liquidity gate (§6)

Before a candidate becomes an order, the option contract must pass:

- Underlying has a **listed options chain**.
- Selected expiration is at least `min_days_to_expiry` out (default 30) and no
  more than `max_days_to_expiry` (default 90) — enough time for the thesis to
  play, capped to limit theta bleed.
- Contract **open interest ≥ `min_open_interest`** (default 100).
- **Bid/ask spread ≤ `max_spread_pct`** of mid (default 15%) — guarantees a
  realistic exit.
- A non-zero bid exists (there is an actual buyer to sell to).

Failing any check → skip the award (fail closed).

---

## 7. Contract selection logic

Given a passing underlying:

- **Direction:** long call (bullish on the award being a positive catalyst).
- **Strike:** configurable moneyness (default: nearest strike slightly OTM,
  e.g. first strike above spot, tunable).
- **Expiration:** nearest listed expiry within the `[min, max]` days window.
- **Quantity:** the largest whole number of contracts whose total debit is
  `≤ min(20% of buying power, max_dollar_per_trade)` and `≥ 1`. If even one
  contract exceeds the cap, **skip**.

---

## 8. Position monitoring & exit

A separate monitor loop, independent of the poller:

- Tracks every open position opened by the bot (persisted, so a restart
  recovers state).
- On each tick, checks unrealized P/L. At `≥ take_profit_pct` (default +50%),
  submits a **sell-to-close** limit order at/near mid.
- No stop-loss order is placed — by design, losers are allowed to **expire
  worthless** (R2). (A configurable time-based exit before expiry is a
  possible v2 addition, default off.)
- Expiry handling: positions left to expire OTM require no action; the broker
  handles expiration. Positions approaching expiry that are ITM but below the
  profit target trigger a close order N days before expiry to avoid
  auto-exercise/assignment mechanics (config: `close_before_expiry_days`,
  default 2).

---

## 9. Architecture

```
                    ┌─────────────────────────────┐
                    │        config (YAML)         │
                    │  risk rules, thresholds,     │
                    │  source list, broker mode    │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────────────────┼───────────────────────────┐
        │                          │                            │
┌───────▼────────┐        ┌────────▼─────────┐        ┌─────────▼────────┐
│  Data pollers  │        │  Signal engine   │        │ Position monitor │
│ (per-source    │──awards▶│ awardee→ticker,  │        │  take-profit,    │
│  adapters)     │        │ tradeability gate│        │  expiry handling │
└───────┬────────┘        └────────┬─────────┘        └─────────┬────────┘
        │                          │ candidate                   │
        │                 ┌────────▼─────────┐                   │
        │                 │   Risk gate      │                   │
        │                 │ (R1–R6, fail     │                   │
        │                 │  closed)         │                   │
        │                 └────────┬─────────┘                   │
        │                          │ approved order              │
        │                 ┌────────▼─────────┐                   │
        │                 │  Broker adapter  │◀──────────────────┘
        │                 │ (Alpaca paper/   │
        │                 │  live)           │
        │                 └────────┬─────────┘
        │                          │
   ┌────▼──────────────────────────▼─────┐
   │   Local state store (SQLite)         │
   │ seen awards, open positions, orders  │
   └──────────────────────────────────────┘
```

### Modules (proposed layout)

```
govt-contract-options/
  DESIGN.md                 # this file
  config.example.yaml       # sane defaults, checked in (no secrets)
  .env.example              # API key names only, no values
  pyproject.toml
  src/gcbot/
    config.py               # load + validate config, enforce invariant bounds
    models.py               # AwardEvent, Candidate, OrderPlan dataclasses
    sources/
      base.py               # AwardSource interface
      usaspending.py
      sam.py
      fpds.py
      defense_gov.py
    resolve/
      ticker.py             # name → ticker, caching, override map
      tradeability.py       # §6 liquidity gate
    risk/
      gate.py               # R1–R6 enforcement (pure, unit-tested)
      sizing.py             # 20% buying-power sizing
    broker/
      base.py               # Broker interface
      alpaca.py             # paper/live via config
      dryrun.py             # logs orders, places nothing (default)
    engine/
      poller.py
      monitor.py
    state/
      store.py              # SQLite persistence
    cli.py                  # entrypoints: run, backfill, status, dry-run
  tests/
    test_risk_gate.py       # invariants R1–R6
    test_sizing.py
    test_tradeability.py
```

---

## 10. Configuration (sane defaults)

`config.example.yaml` — all values overridable; secrets come from env, never
the file.

```yaml
mode: dry_run            # dry_run | paper | live  (dry_run = no orders placed)

risk:
  max_pct_buying_power: 0.20      # R3
  take_profit_pct: 0.50           # R4  (+50%)
  max_dollar_per_trade: null      # optional hard $ cap on top of the 20%
  long_calls_only: true           # R1 (structural; not user-disablable)

signal:
  min_award_dollars: 1000000      # ignore awards below $1M
  set_aside_types: [8a, WOSB, SDVOSB, HUBZone, SBA]  # small-business filter

selection:
  strike_moneyness: first_otm     # first_otm | atm
  min_days_to_expiry: 30
  max_days_to_expiry: 90

tradeability:
  min_open_interest: 100
  max_spread_pct: 0.15
  require_nonzero_bid: true

exit:
  close_before_expiry_days: 2

sources:
  usaspending: { enabled: true,  poll_minutes: 30 }
  sam:         { enabled: true,  poll_minutes: 60 }
  fpds:        { enabled: false, poll_minutes: 60 }
  defense_gov: { enabled: true,  poll_minutes: 60 }
  grants_gov:  { enabled: false, poll_minutes: 240 }
```

Secrets (env / `.env`, never committed):
`ALPACA_API_KEY`, `ALPACA_API_SECRET`, `ALPACA_PAPER` (bool), `SAM_API_KEY`.

---

## 11. Safety & failure modes

Explicit, boring, deterministic handling — fail closed everywhere.

| Failure | Behavior |
|---------|----------|
| Data source down / times out | Log, skip this cycle, retry next interval. Never crash the loop. |
| Ticker resolution ambiguous | Treat as no match. No trade. |
| Buying power fetch fails | Do not size against a stale value. Skip the order. |
| Order rejected by broker (e.g. options not approved) | Log clearly, mark award as attempted, do not retry blindly. |
| Duplicate award seen | Deduped by award key in state store. No double-buy. |
| Bot restarts | State store recovers seen-awards and open-positions; monitor resumes. |
| Spread/liquidity check fails at submit | Skip. Better no fill than a trapped position. |
| Config out of bounds (e.g. max_pct > 1.0) | Refuse to start. Validate on load. |

### Guardrails

- **`dry_run` is the default mode.** It logs the exact order it *would* place
  and submits nothing. Paper and live are explicit opt-ins.
- Risk gate (`risk/gate.py`) is **pure and unit-tested** against R1–R6 so the
  invariants are provable, not incidental.
- A global **daily order cap** and **max concurrent open positions** cap
  (config, defaults TBD) prevent a runaway loop from over-trading.

---

## 12. Known limitations & honest caveats

- **Signal quality is unproven.** Most awardees won't be tradeable; the ones
  that are may not move on a small award. This harness executes a thesis; it
  does not validate one.
- **Timing.** Public award data can lag the market by hours/days; the edge (if
  any) may already be priced in by the time we see it.
- **Options liquidity on small-caps is thin.** The tradeability gate will
  reject a large fraction of otherwise-interesting names — by design.
- **Not financial advice.** This documents a tool the owner asked for; it makes
  no claim the strategy is profitable.

---

## 13. Build order (proposed next steps)

1. **Scaffold** repo layout, `config.py` (+ validation), `models.py`, state
   store, and the `dryrun` broker.
2. **Data layer**: USASpending adapter first (no key needed), then SAM,
   Defense.gov. Print candidate awards — validate signal volume/quality with
   zero trading risk.
3. **Resolve + tradeability**: name→ticker + liquidity gate. See how many
   awards survive to "tradeable."
4. **Risk gate + sizing**, fully unit-tested against R1–R6.
5. **Alpaca adapter** in paper mode; end-to-end dry-run → paper.
6. Run in paper for a while, observe, tune thresholds.
7. Only then consider live, behind an explicit config flip.

---

*This is a design document only. No trading logic has been implemented yet.*
