"""Tests for the check_gas_levels tool and gas-related guardrails."""

import pytest

from agent import tools
from agent.guardrails import MissingDataError


def test_zone_b_methane_value():
    result = tools.check_gas_levels("Zone B")
    assert result["metrics"]["methane"]["value"] == 1.8


def test_zone_b_methane_is_elevated():
    result = tools.check_gas_levels("Zone B")
    # 1.8 >= danger threshold (1.5) -> danger
    assert result["metrics"]["methane"]["status"] == "danger"
    assert result["emergency"] is True


def test_zone_a_is_safe():
    result = tools.check_gas_levels("Zone A")
    assert result["overall_gas_status"] == "ok"
    assert result["emergency"] is False


def test_unknown_zone_raises_no_fabrication():
    # Guardrail: agent must not invent readings for a zone with no data.
    with pytest.raises(MissingDataError):
        tools.check_gas_levels("Zone Z")
