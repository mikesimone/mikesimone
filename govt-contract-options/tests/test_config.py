import pytest

from gcbot.config import ConfigError, parse_config


def test_example_config_is_valid(config):
    assert config.mode == "shadow"
    assert str(config.risk.max_pct_buying_power) == "0.2"
    assert config.risk.long_calls_only is True


@pytest.mark.parametrize(
    "path,value",
    [
        (("risk", "max_pct_buying_power"), 0.25),
        (("risk", "max_pct_buying_power"), 0),
        (("risk", "long_calls_only"), False),
        (("risk", "take_profit_pct"), 0),
        (("risk", "max_dollar_per_trade"), -5),
        (("selection", "max_days_to_expiry"), 10),
        (("tradeability", "max_spread_pct"), 1.5),
        (("exit", "close_before_expiry_days"), 30),
        (("mode",), "yolo"),
    ],
)
def test_out_of_bounds_refuses_to_start(raw_config, path, value):
    target = raw_config
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ConfigError):
        parse_config(raw_config)


def test_unknown_source_rejected(raw_config):
    raw_config["sources"]["robinhood"] = {"enabled": True, "poll_minutes": 5}
    with pytest.raises(ConfigError):
        parse_config(raw_config)
