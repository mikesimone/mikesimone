"""Load and validate config. Out-of-bounds values refuse to start (DESIGN §11)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

MODES = ("dry_run", "shadow", "live")
BROKERS = ("schwab", "alpaca")
MONEYNESS = ("first_otm", "atm")
KNOWN_SOURCES = ("usaspending", "sam", "fpds", "defense_gov", "grants_gov")

# Owner's position-size ceiling. Config may go lower, never higher.
MAX_PCT_BUYING_POWER_CEILING = Decimal("0.20")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class RiskConfig:
    max_pct_buying_power: Decimal
    take_profit_pct: Decimal
    max_dollar_per_trade: Decimal | None
    long_calls_only: bool
    max_orders_per_day: int
    max_open_positions: int


@dataclass(frozen=True)
class SignalConfig:
    min_award_dollars: Decimal
    set_aside_types: tuple[str, ...]


@dataclass(frozen=True)
class SelectionConfig:
    strike_moneyness: str
    min_days_to_expiry: int
    max_days_to_expiry: int


@dataclass(frozen=True)
class TradeabilityConfig:
    min_open_interest: int
    max_spread_pct: Decimal
    require_nonzero_bid: bool


@dataclass(frozen=True)
class PaperConfig:
    ledger_path: str
    run_days: int
    buying_power: Decimal


@dataclass(frozen=True)
class SourceConfig:
    enabled: bool
    poll_minutes: int
    lookback_days: int = 3


@dataclass(frozen=True)
class Config:
    mode: str
    broker: str
    market_data: str
    state_path: str
    paper: PaperConfig
    risk: RiskConfig
    signal: SignalConfig
    selection: SelectionConfig
    tradeability: TradeabilityConfig
    close_before_expiry_days: int
    sources: dict[str, SourceConfig] = field(default_factory=dict)


def _dec(value: Any, name: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ConfigError(f"{name} must be a number, got {value!r}")
    try:
        return Decimal(str(value))
    except Exception as exc:  # decimal.InvalidOperation
        raise ConfigError(f"{name} must be a number, got {value!r}") from exc


def _int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{name} must be an integer, got {value!r}")
    return value


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{name} must be true or false, got {value!r}")
    return value


def _section(raw: dict, name: str) -> dict:
    value = raw.get(name)
    if not isinstance(value, dict):
        raise ConfigError(f"missing or invalid section: {name}")
    return value


def parse_config(raw: dict) -> Config:
    if not isinstance(raw, dict):
        raise ConfigError("config root must be a mapping")

    mode = raw.get("mode")
    if mode not in MODES:
        raise ConfigError(f"mode must be one of {MODES}, got {mode!r}")
    broker = raw.get("broker")
    if broker not in BROKERS:
        raise ConfigError(f"broker must be one of {BROKERS}, got {broker!r}")
    market_data = raw.get("market_data", "schwab")

    r = _section(raw, "risk")
    max_pct = _dec(r.get("max_pct_buying_power"), "risk.max_pct_buying_power")
    if not (Decimal(0) < max_pct <= MAX_PCT_BUYING_POWER_CEILING):
        raise ConfigError(
            f"risk.max_pct_buying_power must be > 0 and <= {MAX_PCT_BUYING_POWER_CEILING}"
        )
    take_profit = _dec(r.get("take_profit_pct"), "risk.take_profit_pct")
    if take_profit <= 0:
        raise ConfigError("risk.take_profit_pct must be > 0")
    max_dollar_raw = r.get("max_dollar_per_trade")
    max_dollar = None
    if max_dollar_raw is not None:
        max_dollar = _dec(max_dollar_raw, "risk.max_dollar_per_trade")
        if max_dollar <= 0:
            raise ConfigError("risk.max_dollar_per_trade must be > 0 or null")
    long_calls_only = _bool(r.get("long_calls_only"), "risk.long_calls_only")
    if not long_calls_only:
        raise ConfigError("risk.long_calls_only is structural and must be true (R1)")
    max_orders = _int(r.get("max_orders_per_day"), "risk.max_orders_per_day")
    max_open = _int(r.get("max_open_positions"), "risk.max_open_positions")
    if max_orders < 1 or max_open < 1:
        raise ConfigError("risk.max_orders_per_day and risk.max_open_positions must be >= 1")
    risk = RiskConfig(max_pct, take_profit, max_dollar, True, max_orders, max_open)

    s = _section(raw, "signal")
    min_award = _dec(s.get("min_award_dollars"), "signal.min_award_dollars")
    if min_award < 0:
        raise ConfigError("signal.min_award_dollars must be >= 0")
    set_asides = s.get("set_aside_types")
    if not isinstance(set_asides, list) or not set_asides:
        raise ConfigError("signal.set_aside_types must be a non-empty list")
    signal = SignalConfig(min_award, tuple(str(x) for x in set_asides))

    sel = _section(raw, "selection")
    moneyness = sel.get("strike_moneyness")
    if moneyness not in MONEYNESS:
        raise ConfigError(f"selection.strike_moneyness must be one of {MONEYNESS}")
    min_dte = _int(sel.get("min_days_to_expiry"), "selection.min_days_to_expiry")
    max_dte = _int(sel.get("max_days_to_expiry"), "selection.max_days_to_expiry")
    if min_dte < 1 or max_dte < min_dte:
        raise ConfigError("selection days-to-expiry window is invalid")
    selection = SelectionConfig(moneyness, min_dte, max_dte)

    t = _section(raw, "tradeability")
    min_oi = _int(t.get("min_open_interest"), "tradeability.min_open_interest")
    if min_oi < 0:
        raise ConfigError("tradeability.min_open_interest must be >= 0")
    spread = _dec(t.get("max_spread_pct"), "tradeability.max_spread_pct")
    if not (Decimal(0) < spread <= Decimal(1)):
        raise ConfigError("tradeability.max_spread_pct must be > 0 and <= 1")
    nonzero_bid = _bool(t.get("require_nonzero_bid"), "tradeability.require_nonzero_bid")
    tradeability = TradeabilityConfig(min_oi, spread, nonzero_bid)

    p = _section(raw, "paper")
    paper_bp = _dec(p.get("buying_power"), "paper.buying_power")
    if paper_bp <= 0:
        raise ConfigError("paper.buying_power must be > 0")
    paper = PaperConfig(
        ledger_path=str(p.get("ledger_path", "data/paper_ledger.csv")),
        run_days=_int(p.get("run_days", 30), "paper.run_days"),
        buying_power=paper_bp,
    )

    e = _section(raw, "exit")
    close_days = _int(e.get("close_before_expiry_days"), "exit.close_before_expiry_days")
    if close_days < 0 or close_days >= min_dte:
        raise ConfigError("exit.close_before_expiry_days must be >= 0 and < min_days_to_expiry")

    sources: dict[str, SourceConfig] = {}
    for name, sc in _section(raw, "sources").items():
        if name not in KNOWN_SOURCES:
            raise ConfigError(f"unknown source: {name}")
        if not isinstance(sc, dict):
            raise ConfigError(f"sources.{name} must be a mapping")
        poll = _int(sc.get("poll_minutes"), f"sources.{name}.poll_minutes")
        lookback = _int(sc.get("lookback_days", 3), f"sources.{name}.lookback_days")
        if poll < 1 or lookback < 1:
            raise ConfigError(f"sources.{name} poll_minutes and lookback_days must be >= 1")
        sources[name] = SourceConfig(_bool(sc.get("enabled"), f"sources.{name}.enabled"), poll, lookback)

    return Config(
        mode=mode,
        broker=broker,
        market_data=str(market_data),
        state_path=str(raw.get("state_path", "data/state.sqlite3")),
        paper=paper,
        risk=risk,
        signal=signal,
        selection=selection,
        tradeability=tradeability,
        close_before_expiry_days=close_days,
        sources=sources,
    )


def load_config(path: str | Path) -> Config:
    with open(path, encoding="utf-8") as fh:
        return parse_config(yaml.safe_load(fh))
