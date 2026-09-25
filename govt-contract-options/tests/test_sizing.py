from dataclasses import replace
from decimal import Decimal as D

from gcbot.risk.sizing import contracts_for, max_debit, take_profit_price


def test_twenty_percent_cap(config):
    # $10,000 BP -> $2,000 cap; $1.50 premium = $150/contract -> 13 contracts ($1,950).
    assert max_debit(D("10000"), config.risk) == D("2000")
    assert contracts_for(D("1.50"), D("10000"), config.risk) == 13


def test_exact_fit_is_allowed(config):
    assert contracts_for(D("2.00"), D("10000"), config.risk) == 10


def test_one_contract_over_cap_skips(config):
    assert contracts_for(D("25.00"), D("10000"), config.risk) == 0


def test_dollar_cap_tightens(config):
    risk = replace(config.risk, max_dollar_per_trade=D("500"))
    assert contracts_for(D("1.50"), D("10000"), risk) == 3


def test_bad_inputs_size_to_zero(config):
    assert contracts_for(D("0"), D("10000"), config.risk) == 0
    assert contracts_for(D("1"), D("0"), config.risk) == 0


def test_take_profit_price(config):
    assert take_profit_price(D("1.50"), config.risk) == D("2.25")
