"""MineOps Agent: interprets a supervisor question, plans a tool sequence,
executes tools, reasons over results, and returns a grounded response.

This is a rule/intent-based agent (no external LLM key required) so it runs
fully offline and deterministically. The agentic behavior comes from dynamic
tool selection: different questions produce different tool sequences.
"""

import re

from . import tools
from .config import KNOWN_ZONES
from .guardrails import MissingDataError, EMERGENCY_NOTICE


class ToolLogger:
    """Records every tool call for transparency / auditing."""

    def __init__(self):
        self.calls = []

    def record(self, name, args, ok, error=None):
        self.calls.append({"tool": name, "args": args, "ok": ok, "error": error})

    def formatted(self):
        lines = []
        for c in self.calls:
            mark = "OK" if c["ok"] else "FAIL"
            arg = c["args"] if c["args"] else "-"
            line = f"  [{mark}] {c['tool']}({arg})"
            if c["error"]:
                line += f" -> {c['error']}"
            lines.append(line)
        return "\n".join(lines)


def _detect_zone(question):
    q = question.lower()
    for zone in KNOWN_ZONES:
        # match "zone b" or "b"
        letter = zone.split()[-1].lower()
        if zone.lower() in q or re.search(rf"\bzone\s*{letter}\b", q):
            return zone
    # Detect an unrecognized zone reference (e.g. "Zone Z") so the tools can
    # honestly report missing data instead of the agent silently ignoring it.
    m = re.search(r"\bzone\s*([a-z0-9]+)\b", q)
    if m:
        return f"Zone {m.group(1).upper()}"
    return None


def _plan(question):
    """Decide which tools to run based on the question's intent.

    Returns (intent, plan_description, list_of_(tool_name, kwargs)).
    """
    q = question.lower()
    zone = _detect_zone(question)

    # Zone safety assessment -> full multi-step chain.
    if ("safe" in q or "safety" in q) and zone:
        return (
            "zone_safety",
            [
                "Check current gas readings",
                "Check recent incidents",
                "Check ventilation / equipment status",
                "Calculate risk and generate an action plan",
            ],
            [("generate_supervisor_action_plan", {"zone": zone})],
        )

    # Equipment maintenance.
    if any(w in q for w in ["maintenance", "equipment", "repair", "service", "fault", "broken"]):
        return (
            "equipment",
            ["Inspect equipment status", "Identify items needing urgent maintenance"],
            [("inspect_equipment_status", {"zone": zone})],
        )

    # Methane / gas specific.
    if any(w in q for w in ["methane", "gas", "co ", "carbon monoxide"]) and zone:
        return (
            "gas_check",
            ["Check gas readings", "Generate action plan if elevated"],
            [
                ("check_gas_levels", {"zone": zone}),
                ("generate_supervisor_action_plan", {"zone": zone}),
            ],
        )

    # Which zone to inspect first / ranking.
    if any(w in q for w in ["inspect first", "which zone", "rank", "priorit", "most risk", "riskiest"]):
        return (
            "rank",
            ["Rank all zones by combined risk", "Recommend inspection order"],
            [("rank_zone_risk", {})],
        )

    # Last-shift / general safety risks.
    if any(w in q for w in ["last shift", "shift", "risks", "today", "incidents", "summarize", "summary"]):
        return (
            "shift_summary",
            [
                "Summarize incidents",
                "Check gas readings across zones",
                "Inspect equipment status",
            ],
            [
                ("summarize_incidents", {"zone": zone}),
                ("inspect_equipment_status", {"zone": zone}),
            ],
        )

    # Fallback: rank zones so the supervisor gets something useful.
    return (
        "fallback_rank",
        ["Question intent unclear; rank zones by risk as a general overview"],
        [("rank_zone_risk", {})],
    )


def _confidence(logger, results):
    """Simple confidence score based on how much data was available."""
    if not logger.calls:
        return 0.0
    ok = sum(1 for c in logger.calls if c["ok"])
    base = ok / len(logger.calls)
    # Penalize if any tool hit missing data.
    if any(not c["ok"] for c in logger.calls):
        base *= 0.7
    return round(base, 2)


def ask(question):
    """Main entry point. Returns a dict with plan, results, answer, log, confidence."""
    logger = ToolLogger()
    intent, plan, steps = _plan(question)
    results = []

    for name, kwargs in steps:
        fn = getattr(tools, name)
        arg_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        try:
            result = fn(**kwargs)
            logger.record(name, arg_str, True)
            results.append(result)
        except MissingDataError as e:
            logger.record(name, arg_str, False, str(e))
            results.append({"tool": name, "error": str(e)})

    answer = _render_answer(intent, question, results)
    return {
        "question": question,
        "intent": intent,
        "plan": plan,
        "tool_log": logger.formatted(),
        "results": results,
        "answer": answer,
        "confidence": _confidence(logger, results),
    }


def _render_answer(intent, question, results):
    """Turn structured tool results into a supervisor-facing answer."""
    lines = []

    for r in results:
        if r.get("error"):
            lines.append(f"NOTE: {r['error']}")

    plan_result = next((r for r in results if r.get("tool") == "generate_supervisor_action_plan"), None)
    rank_result = next((r for r in results if r.get("tool") == "rank_zone_risk"), None)
    eq_result = next((r for r in results if r.get("tool") == "inspect_equipment_status"), None)
    gas_result = next((r for r in results if r.get("tool") == "check_gas_levels"), None)
    inc_result = next((r for r in results if r.get("tool") == "summarize_incidents"), None)

    if plan_result:
        lines.append(f"Risk Level: {plan_result['risk_level'].upper()}")
        if plan_result["evidence"]:
            lines.append("Evidence:")
            for e in plan_result["evidence"]:
                lines.append(f"  - {e}")
        lines.append("Recommended actions:")
        for a in plan_result["actions"]:
            lines.append(f"  - {a}")
        if plan_result["emergency"]:
            lines.append("")
            lines.append(EMERGENCY_NOTICE)

    if rank_result:
        lines.append(f"Recommended inspection order (highest risk first): "
                     f"{rank_result['inspect_first']}")
        for z in rank_result["ranking"]:
            reason = "; ".join(z["reasons"]) if z["reasons"] else "no elevated factors"
            lines.append(f"  - {z['zone']}: {z['risk_level']} (score {z['score']}) - {reason}")

    if eq_result and not plan_result:
        urgent = [i for i in eq_result["equipment"] if i["needs_maintenance"]]
        if urgent:
            lines.append("Equipment needing maintenance:")
            for i in sorted(urgent, key=lambda x: 0 if x["urgency"] == "urgent" else 1):
                fault = f" - {i['fault']}" if i.get("fault") else ""
                lines.append(f"  - [{i['urgency'].upper()}] {i['type']} {i['id']} "
                             f"(zone {i['zone']}, status {i['status']}{fault})")
        else:
            lines.append("No equipment currently flagged for maintenance.")

    if gas_result and not plan_result:
        lines.append(f"Gas readings for {gas_result['zone']} "
                     f"(overall: {gas_result['overall_gas_status']}):")
        for m, info in gas_result["metrics"].items():
            lines.append(f"  - {m}: {info['value']} ({info['status']})")

    if inc_result and not plan_result:
        lines.append(f"Incidents ({inc_result['count']} total, "
                     f"{inc_result['high_severity_count']} high-severity):")
        for i in inc_result["incidents"]:
            lines.append(f"  - [{i['severity']}] {i['type']} in {i['zone']} "
                         f"at {i['timestamp']}: {i['description']}")

    if not lines:
        lines.append("No relevant data found for this question.")

    return "\n".join(lines)
