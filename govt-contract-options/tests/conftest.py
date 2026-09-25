from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from gcbot.config import parse_config

EXAMPLE = Path(__file__).resolve().parent.parent / "config.example.yaml"


@pytest.fixture
def raw_config() -> dict:
    with open(EXAMPLE, encoding="utf-8") as fh:
        return copy.deepcopy(yaml.safe_load(fh))


@pytest.fixture
def config(raw_config):
    return parse_config(raw_config)
