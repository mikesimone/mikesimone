from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from gcbot.models import AccountSnapshot, OptionQuote, OrderPlan
from gcbot.risk.gate import check_order

TODAY = date(2026, 9, 25)
EXPIRY = TODAY + timedelta(days=45)


@pytest.fixture
def quote():
    return OptionQuote(
        option_symbol="ABC   261109C00020000",
        underlying="ABC",
        right="CALL",
        strike=D("20"),
        expiry=EXPIRY,
        bid=D("1.45"),
        ask=D("1.55"),
        open_interest=500,
    )


@pytest.fixture
def plan(quote):
    return OrderPlan(
        award_key="CONT_AWD_X",
        underlying="ABC",
        option_symbol=quote.option_symbol,
        right="CALL",
        side="BUY_TO_OPEN",
        qty=10,
        limit_price=D("1.50"),
        expiry=EXPIRY,
        take_profit_price=D("2.25"),
    )


@pytest.fixture
def account():
    return AccountSnapshot(buying_power=D("10000"), orders_today=0, open_positions=0)


def run(plan, quote, account, config):
    return check_order(plan, quote, account, config, TODAY)


def codes(result):
    return {v.split(":")[0] for v in result.violations}


def test_clean_order_approved(plan, quote, account, config):
    result = run(plan, quote, account, config)
    assert result.approved, result.violations


def test_r1_rejects_put(plan, quote, account, config):
    assert "R1" in codes(run(replace(plan, right="PUT"), quote, account, config))


@pytest.mark.parametrize("side", ["SELL_TO_OPEN", "SELL_TO_CLOSE", "BUY_TO_CLOSE"])
def test_r1_rejects_non_buy_to_open(plan, quote, account, config, side):
    assert "R1" in codes(run(replace(plan, side=side), quote, account, config))


def test_r1_rejects_plan_quote_mismatch(plan, quote, account, config):
    assert "R1" in codes(run(replace(plan, option_symbol="OTHER"), quote, account, config))


def test_r2_rejects_zero_qty_and_price(plan, quote, account, config):
    assert "R2" in codes(run(replace(plan, qty=0), quote, account, config))
    assert "R2" in codes(run(replace(plan, limit_price=D("0")), quote, account, config))


def test_r3_rejects_over_twenty_percent(plan, quote, account, config):
    # 14 x $150 = $2,100 > $2,000 cap
    assert "R3" in codes(run(replace(plan, qty=14), quote, account, config))


def test_r3_fails_closed_without_buying_power(plan, quote, account, config):
    assert "R3" in codes(run(plan, quote, replace(account, buying_power=None), config))


def test_r4_rejects_wrong_take_profit(plan, quote, account, config):
    assert "R4" in codes(run(replace(plan, take_profit_price=D("5.00")), quote, account, config))


def test_r6_rejects_wide_spread(plan, quote, account, config):
    wide = replace(quote, bid=D("1.00"), ask=D("2.00"))
    assert "R6" in codes(run(plan, wide, account, config))


def test_r6_rejects_no_bid(plan, quote, account, config):
    assert "R6" in codes(run(plan, replace(quote, bid=D("0")), account, config))


def test_r6_rejects_thin_open_interest(plan, quote, account, config):
    assert "R6" in codes(run(plan, replace(quote, open_interest=5), account, config))


def test_r6_rejects_expiry_outside_window(plan, quote, account, config):
    near = TODAY + timedelta(days=10)
    result = run(replace(plan, expiry=near), replace(quote, expiry=near), account, config)
    assert "R6" in codes(result)


def test_daily_and_open_caps(plan, quote, account, config):
    assert "cap" in codes(run(plan, quote, replace(account, orders_today=3), config))
    assert "cap" in codes(run(plan, quote, replace(account, open_positions=5), config))
