"""Tests for agent tool-selection (the agentic behavior) and guardrails.

These are the 'safe vs unsafe recommendation' evaluation examples.
"""

from agent.agent import ask


def test_different_questions_select_different_tools():
    gas = ask("Is Zone B safe for workers right now?")
    equip = ask("Which equipment needs urgent maintenance?")
    rank = ask("Which zone should be inspected first?")

    assert gas["intent"] == "zone_safety"
    assert equip["intent"] == "equipment"
    assert rank["intent"] == "rank"


def test_unsafe_zone_b_is_high_risk_and_restricts_access():
    resp = ask("Is Zone B safe for workers right now?")
    assert "Risk Level: HIGH" in resp["answer"]
    assert "Restrict worker access" in resp["answer"]
    # Guardrail: emergency notice must appear, not an "ok to continue" message.
    assert "emergency protocol" in resp["answer"].lower()


def test_safe_zone_a_is_low_risk():
    resp = ask("Is Zone A safe for workers right now?")
    assert "Risk Level: LOW" in resp["answer"]


def test_missing_data_is_reported_not_fabricated():
    resp = ask("Is Zone Z safe for workers right now?")
    assert "No gas readings available for Zone Z" in resp["answer"] or \
           "No equipment records available for Zone Z" in resp["answer"]


def test_zone_ranking_orders_by_risk():
    resp = ask("Which zone should be inspected first?")
    ranking = resp["results"][0]["ranking"]
    scores = [z["score"] for z in ranking]
    assert scores == sorted(scores, reverse=True)
