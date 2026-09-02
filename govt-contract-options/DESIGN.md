# Government Contract Options Bot — Design Document

**Status:** Draft (design phase — no trading code yet)
**Author:** Design pass for the automated contract-award options watcher
**Stack:** Python 3.11+, Schwab Trader API (live) + local shadow-ledger paper mode, official government data APIs

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

## 3. Broker choice: Schwab (primary)

**Decision: Charles Schwab Trader API as the live broker. Validation happens
via a local shadow-ledger paper mode (§8.1), not a broker sandbox. Alpaca is
kept as an optional broker-paper fallback only.**

Rationale for Schwab:

- **Official, supported API.** The **Schwab Trader API**
  (`developer.schwab.com`) — successor to the retired TD Ameritrade API after
  Schwab absorbed TDA — is OAuth 2.0, official, and trades your real Schwab
  brokerage account. Not reverse-engineered.
- **Options approval already in place** on the owner's Schwab account — no
  second approval process to start over on.
- Mature community wrappers around the *official* API exist
  (`schwab-py`, `schwabdev`), so we don't hand-roll OAuth.
- Two registrable products: **"Accounts and Trading" (Trader API)** for
  orders/positions and **"Market Data"** for quotes and option chains. Both
  support options.

### Schwab-specific constraints (design must accommodate)

| Constraint | Impact on this build |
|-----------|----------------------|
| **No paper/sandbox environment.** Every Trader-API order is a real live order against real money. | Broker-side paper isn't available. Pre-live validation uses the **local shadow ledger (§8.1)** instead. `dry_run` and shadow mode carry the validation weight Alpaca paper would have. |
| **App approval gate.** A registered app sits "pending" until Schwab **approves it for production**; can take days. | One-time manual prerequisite before any live order. Doesn't block dry-run/shadow work, which needs only market data (read-only). |
| **Refresh token expires every 7 days** and re-auth needs a browser login step. | Bot needs a small re-auth helper and a weekly manual login. Token store + refresh handling is an explicit part of the Schwab adapter. |

### Why not Robinhood

Robinhood has **no official public trading API**. The only access is
unofficial reverse-engineered libraries hitting its private mobile endpoints,
which violate its Terms of Service, break without notice, and risk account
lockout. That path is explicitly rejected for this build.

### Alpaca (optional fallback only)

Alpaca remains documented because it offers a genuine free **broker paper
environment** with real market data, which Schwab lacks. If we ever want
broker-side paper fills (rather than the local shadow ledger), the Alpaca
adapter provides it. Not the primary path.

### Account prerequisites (manual, one-time)

- Schwab brokerage account with **options approval** (already held).
- Register a developer app at `developer.schwab.com` for both the **Trader
  API** and **Market Data API**; obtain **App Key + Secret**.
- Get the app **approved for production** before enabling `live` mode.
- Complete the initial OAuth login to mint the first refresh token; plan for
  weekly re-auth.
- Market Data API access is enough on its own for `dry_run` and `shadow`
  modes (read-only quotes/chains) — no production trading approval needed to
  start validating.

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

### 8.1 Local paper mode (shadow ledger)

Because Schwab has no paper/sandbox, pre-live validation is done with a
**local shadow ledger** — the bot records what it *would* have bought and
re-scores those hypothetical positions daily against real market data. No
broker order is ever placed in this mode. Intended to run for ~a month before
any live trading.

**On signal (shadow mode):** instead of submitting an order, append one row to
`paper_ledger.csv` capturing exactly the trade that would have been placed:

| Column | Meaning |
|--------|---------|
| `entry_ts` | When the signal fired |
| `award_ref` | Source award key (PIID / award ID) that triggered it |
| `ticker` | Underlying |
| `option_symbol` | The specific contract (OCC symbol) |
| `right` | Always `CALL` (R1) |
| `strike` | Strike price |
| `expiry` | Contract expiration date |
| `entry_price` | Per-contract premium we would have paid (ask/mid at signal) |
| `qty` | Number of contracts (from the §7 sizing, capped at 20% BP) |
| `debit` | `entry_price × qty × 100` — the capital at risk |
| `take_profit_price` | `entry_price × (1 + take_profit_pct)` |
| `status` | `OPEN` at entry |
| `exit_ts`, `exit_price`, `realized_pl`, `outcome` | Filled in when the row closes |

**Daily mark (`paper-mark` job, once per day):** for every `OPEN` row, pull a
current option quote (read-only market data — Schwab Market Data API or
whichever quote source is configured) and apply the *same* exit rules the live
monitor would:

1. **Profit target hit** — if current bid ≥ `take_profit_price`:
   `status=CLOSED`, `outcome=PROFIT`, `exit_price` = current bid,
   `realized_pl = (exit_price − entry_price) × qty × 100`.
2. **Expired** — if today > `expiry` and not already closed: settle at
   expiration intrinsic value (OTM → `0`, i.e. **expired worthless**; ITM →
   intrinsic). `status=EXPIRED`, `outcome=WORTHLESS` or `EXPIRED_ITM`,
   `realized_pl` = settlement − debit (a loss capped at the debit, per R2).
3. **Still open** — otherwise leave `OPEN`, optionally stamping a
   `last_mark_price` / `last_mark_ts` for the running unrealized view.

**Reporting:** a `paper-report` command summarizes the ledger — count of
open/closed/expired, total hypothetical P/L, win rate, average hold time —
so after ~a month there's a concrete read on whether the signal is worth real
money. This is deterministic and fully offline from any order placement.

Notes:
- Fills are **optimistic-but-honest**: entry at the ask/mid we actually
  observed, exit at the real bid on the mark day. No look-ahead — each mark
  uses only data available on that date.
- The shadow ledger reuses the **same risk gate and sizing** as live, so it
  validates the whole decision path, not just the idea.
- `dry_run` (log-only, nothing persisted) and `shadow` (CSV ledger, daily
  marks) are distinct; `shadow` is the month-long validation mode, `dry_run`
  is a quick "show me what it would do right now."

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
        │                 │  Execution sink  │◀──────────────────┘
        │                 │ shadow: CSV ledger│
        │                 │ live: Schwab API  │
        │                 │ dry_run: log only │
        │                 └────────┬─────────┘
        │                          │
   ┌────▼──────────────────────────▼─────┐
   │   Local state store (SQLite + CSV)   │
   │ seen awards, positions, paper ledger │
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
      schwab.py             # PRIMARY: OAuth, token refresh, live orders
      alpaca.py             # optional broker-paper fallback
      dryrun.py             # logs orders, places nothing
    marketdata/
      base.py               # read-only quote/chain interface
      schwab.py             # Schwab Market Data API (quotes, option chains)
    paper/
      ledger.py             # shadow ledger: append signal, daily mark, report (§8.1)
    engine/
      poller.py
      monitor.py            # live exit loop (take-profit, expiry)
    state/
      store.py              # SQLite persistence (seen awards, live positions)
    cli.py                  # run, backfill, status, dry-run,
                            #   paper-mark, paper-report, schwab-auth
  data/
    paper_ledger.csv        # shadow-mode hypothetical trades (git-ignored)
  tests/
    test_risk_gate.py       # invariants R1–R6
    test_sizing.py
    test_tradeability.py
    test_paper_ledger.py    # entry/mark/expiry accounting
```

---

## 10. Configuration (sane defaults)

`config.example.yaml` — all values overridable; secrets come from env, never
the file.

```yaml
mode: shadow             # dry_run | shadow | live
                         #   dry_run = log only, nothing persisted
                         #   shadow  = local CSV ledger + daily marks (§8.1), no broker orders
                         #   live    = real Schwab orders

broker: schwab           # schwab (primary) | alpaca (optional broker-paper fallback)
market_data: schwab      # read-only quote/chain source (used by shadow + live)

paper:                   # shadow-mode ledger settings
  ledger_path: data/paper_ledger.csv
  run_days: 30           # intended validation window before considering live

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
`SCHWAB_APP_KEY`, `SCHWAB_APP_SECRET`, `SCHWAB_CALLBACK_URL`,
`SCHWAB_TOKEN_PATH` (path to the cached OAuth token file), `SAM_API_KEY`.
Optional fallback: `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `ALPACA_PAPER`.

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
| Schwab refresh token expired (7-day) | Live mode refuses to place orders and surfaces a clear "re-auth needed" message; `schwab-auth` command re-mints it. Never trades on a stale token. |
| Quote source unavailable during a shadow daily-mark | Skip that mark for the day; row stays `OPEN`. Marks are idempotent, so a missed day self-heals on the next run. |
| `mode: live` selected but app not production-approved | Refuse to start live; direct to dry_run/shadow. |

### Guardrails

- **`shadow` is the default working mode** (local ledger, no broker orders);
  `dry_run` logs without persisting; `live` is an explicit, deliberate opt-in
  that additionally requires a production-approved Schwab app and a valid
  token.
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
5. **Shadow ledger (§8.1)**: wire signals → `paper_ledger.csv`, plus the
   `paper-mark` (daily re-score) and `paper-report` commands. Needs only a
   read-only quote source, so no live trading approval required to start.
6. **Run in shadow mode ~a month.** Review the ledger report — win rate,
   hypothetical P/L, how many signals were even tradeable — and tune
   thresholds. This is the real go/no-go on the strategy.
7. **Schwab adapter**: OAuth + token refresh (`schwab-auth`), Market Data for
   quotes/chains, and live order placement. Validate end-to-end in `dry_run`
   first (real signals, real quotes, no orders).
8. Only after a convincing shadow run **and** production app approval, flip to
   `live` behind an explicit config change — start with minimal size.
9. *(Optional)* Alpaca broker-paper adapter if we ever want broker-side paper
   fills instead of the local ledger.

---

*This is a design document only. No trading logic has been implemented yet.*
