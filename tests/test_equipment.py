"""Tests for the inspect_equipment_status tool."""

import pytest

from agent import tools
from agent.guardrails import MissingDataError


def test_zone_b_contains_ventilation_fan():
    result = tools.inspect_equipment_status("Zone B")
    ids = [e["id"] for e in result["equipment"]]
    assert "HV-101" in ids


def test_critical_equipment_flagged_urgent():
    result = tools.inspect_equipment_status()
    # CB-410 is critical (motor overheating) -> urgent.
    assert "CB-410" in result["urgent_ids"]


def test_high_operating_hours_flagged():
    result = tools.inspect_equipment_status("Zone C")
    cb = next(e for e in result["equipment"] if e["id"] == "CB-410")
    assert cb["needs_maintenance"] is True


def test_unknown_zone_raises():
    with pytest.raises(MissingDataError):
        tools.inspect_equipment_status("Zone Z")
