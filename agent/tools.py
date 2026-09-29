"""MineOps Agent tools.

Each tool reads structured data and returns a structured dict. Tools never
fabricate values: if data is missing they raise MissingDataError (caught by the
agent and surfaced honestly to the user).
"""

from . import data_store
from .config import GAS_THRESHOLDS, OPERATING_HOURS_LIMIT
from .guardrails import MissingDataError, require_zone_data, is_emergency


def _classify_gas(reading):
    """Return per-metric status (ok/warning/danger) and worst overall level."""
    metrics = {}
    worst = "ok"
    order = {"ok": 0, "warning": 1, "danger": 2}
    for metric, limits in GAS_THRESHOLDS.items():
        value = reading.get(metric)
        if value is None:
            metrics[metric] = {"value": None, "status": "no_data"}
            continue
        if value >= limits["danger"]:
            status = "danger"
        elif value >= limits["warning"]:
            status = "warning"
        else:
            status = "ok"
        metrics[metric] = {"value": value, "status": status}
        if order[status] > order[worst]:
            worst = status
    return metrics, worst


def check_gas_levels(zone):
    """Return classified gas readings for a zone.

    Raises MissingDataError if the zone has no gas records.
    """
    readings = require_zone_data(zone, data_store.get_gas_readings(), "gas readings")
    reading = readings[0]
    metrics, worst = _classify_gas(reading)
    return {
        "tool": "check_gas_levels",
        "zone": zone,
        "timestamp": reading.get("timestamp"),
        "metrics": metrics,
        "overall_gas_status": worst,
        "emergency": is_emergency(reading),
    }


def inspect_equipment_status(zone=None):
    """Return equipment health, optionally filtered by zone.

    Flags equipment as needing maintenance if status is warning/critical or if
    operating hours exceed the overhaul limit.
    """
    equipment = data_store.get_equipment()
    if zone is not None:
        equipment = [e for e in equipment if e.get("zone") == zone]
        if not equipment:
            raise MissingDataError(
                f"No equipment records available for {zone}."
            )

    items = []
    for e in equipment:
        needs_maintenance = (
            e.get("status") in ("warning", "critical")
            or (e.get("operating_hours") or 0) >= OPERATING_HOURS_LIMIT
        )
        urgency = "none"
        if e.get("status") == "critical":
            urgency = "urgent"
        elif e.get("status") == "warning" or (e.get("operating_hours") or 0) >= OPERATING_HOURS_LIMIT:
            urgency = "soon"
        items.append({
            "id": e["id"],
            "type": e["type"],
            "zone": e["zone"],
            "status": e["status"],
            "operating_hours": e.get("operating_hours"),
            "last_service": e.get("last_service"),
            "fault": e.get("fault"),
            "needs_maintenance": needs_maintenance,
            "urgency": urgency,
        })

    return {
        "tool": "inspect_equipment_status",
        "zone": zone,
        "equipment": items,
        "urgent_ids": [i["id"] for i in items if i["urgency"] == "urgent"],
    }


def summarize_incidents(zone=None):
    """Summarize incident records, optionally filtered by zone."""
    incidents = data_store.get_incidents()
    if zone is not None:
        incidents = [i for i in incidents if i.get("zone") == zone]

    severity_rank = {"Low": 1, "Medium": 2, "High": 3}
    incidents_sorted = sorted(
        incidents, key=lambda i: severity_rank.get(i.get("severity"), 0), reverse=True
    )
    high = [i for i in incidents_sorted if i.get("severity") == "High"]

    return {
        "tool": "summarize_incidents",
        "zone": zone,
        "count": len(incidents_sorted),
        "high_severity_count": len(high),
        "incidents": incidents_sorted,
    }


def rank_zone_risk():
    """Rank all known zones by combined gas, incident, and equipment risk."""
    from .config import KNOWN_ZONES

    scored = []
    for zone in KNOWN_ZONES:
        score = 0
        reasons = []

        # Gas contribution.
        try:
            gas = check_gas_levels(zone)
            if gas["overall_gas_status"] == "danger":
                score += 3
                reasons.append("gas reading at danger level")
            elif gas["overall_gas_status"] == "warning":
                score += 2
                reasons.append("gas reading elevated")
        except MissingDataError:
            reasons.append("no gas data")

        # Incident contribution.
        inc = summarize_incidents(zone)
        score += inc["high_severity_count"] * 2
        if inc["high_severity_count"]:
            reasons.append(f"{inc['high_severity_count']} high-severity incident(s)")

        # Equipment contribution.
        try:
            eq = inspect_equipment_status(zone)
            urgent = len(eq["urgent_ids"])
            score += urgent * 2
            if urgent:
                reasons.append(f"{urgent} critical equipment item(s)")
        except MissingDataError:
            pass

        if score >= 5:
            level = "High"
        elif score >= 2:
            level = "Medium"
        else:
            level = "Low"

        scored.append({"zone": zone, "score": score, "risk_level": level, "reasons": reasons})

    scored.sort(key=lambda z: z["score"], reverse=True)
    return {
        "tool": "rank_zone_risk",
        "ranking": scored,
        "inspect_first": scored[0]["zone"] if scored else None,
    }


def generate_supervisor_action_plan(zone):
    """Produce a grounded action plan for a zone based on verified data.

    Combines gas, incidents, and equipment. Defers to emergency protocol when a
    danger-level reading is present.
    """
    evidence = []
    actions = []
    emergency = False
    risk_score = 0

    # Gas.
    try:
        gas = check_gas_levels(zone)
        for metric, info in gas["metrics"].items():
            if info["status"] in ("warning", "danger"):
                evidence.append(f"{metric}={info['value']} ({info['status']})")
        if gas["emergency"]:
            emergency = True
            risk_score += 3
        elif gas["overall_gas_status"] == "warning":
            risk_score += 2
    except MissingDataError as e:
        evidence.append(str(e))

    # Incidents.
    inc = summarize_incidents(zone)
    if inc["high_severity_count"]:
        risk_score += inc["high_severity_count"] * 2
        for i in inc["incidents"]:
            if i.get("severity") == "High":
                evidence.append(f"High-severity {i['type']} at {i['timestamp']}")

    # Equipment.
    try:
        eq = inspect_equipment_status(zone)
        for item in eq["equipment"]:
            if item["needs_maintenance"]:
                risk_score += 2 if item["urgency"] == "urgent" else 1
                evidence.append(
                    f"{item['type']} {item['id']} status={item['status']}"
                    + (f" ({item['fault']})" if item.get("fault") else "")
                )
    except MissingDataError as e:
        evidence.append(str(e))

    if emergency or risk_score >= 5:
        risk_level = "High"
    elif risk_score >= 2:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    # Build actions grounded in the evidence.
    if risk_level == "High":
        actions.append(f"Restrict worker access to {zone}.")
        actions.append("Have qualified safety personnel assess the situation on site.")
    if any("methane" in e for e in evidence):
        actions.append("Re-check methane readings and follow the mine's gas/emergency protocol.")
    if any("Ventilation Fan" in e for e in evidence):
        actions.append("Inspect the ventilation system and confirm airflow is restored.")
    if any("status=critical" in e for e in evidence):
        actions.append("Take critical equipment offline and schedule urgent maintenance.")
    if risk_level == "Medium":
        actions.append(f"Schedule an inspection of {zone} and monitor readings closely.")
    if risk_level == "Low" and not actions:
        actions.append(f"No urgent action required for {zone}. Continue routine monitoring.")

    return {
        "tool": "generate_supervisor_action_plan",
        "zone": zone,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "emergency": emergency,
        "evidence": evidence,
        "actions": actions,
    }
