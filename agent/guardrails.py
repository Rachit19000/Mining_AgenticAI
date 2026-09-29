"""Safety guardrails for the MineOps Agent.

Core rules:
1. Never invent sensor readings. If data is missing, say so explicitly.
2. Never override or downgrade emergency protocols. When a dangerous reading is
   present, the recommendation must defer to established mine safety procedures
   and human authority.
"""

from .config import GAS_THRESHOLDS


class MissingDataError(Exception):
    """Raised when requested data does not exist. Prevents fabrication."""


def require_zone_data(zone, records, data_label):
    """Return records for a zone or raise if none exist.

    This is the anti-hallucination guard: tools must not synthesize values for
    zones that have no records.
    """
    matches = [r for r in records if r.get("zone") == zone]
    if not matches:
        raise MissingDataError(
            f"No {data_label} available for {zone}. "
            f"Cannot assess this factor from the current data."
        )
    return matches


def is_emergency(gas_reading):
    """True if any gas value is at or above its danger threshold."""
    if not gas_reading:
        return False
    for metric, limits in GAS_THRESHOLDS.items():
        value = gas_reading.get(metric)
        if value is not None and value >= limits["danger"]:
            return True
    return False


EMERGENCY_NOTICE = (
    "This reading indicates a potential emergency-level hazard. Do NOT allow "
    "work to continue based on this assessment alone. Follow the mine's "
    "established emergency protocol and have qualified safety personnel assess "
    "the situation. This assistant supports supervisors and does not replace "
    "human authority or regulated safety procedures."
)
