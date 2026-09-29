"""Central configuration: safety thresholds and data paths.

Thresholds are based on illustrative mining safety limits. They are kept in one
place so the guardrails and tools share a single source of truth.
"""

import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Illustrative action thresholds. Values at or above these levels are treated
# as elevated / dangerous. Real mines must use their own regulated limits.
GAS_THRESHOLDS = {
    # methane % by volume. >= 1.0% is treated as elevated in this demo.
    "methane": {"warning": 1.0, "danger": 1.5},
    # carbon monoxide in ppm.
    "carbon_monoxide": {"warning": 15, "danger": 25},
    # temperature in Celsius.
    "temperature": {"warning": 32, "danger": 38},
    # dust in mg/m^3.
    "dust": {"warning": 2.0, "danger": 3.0},
}

# Equipment maintenance thresholds.
OPERATING_HOURS_LIMIT = 10000  # hours before overhaul is recommended

KNOWN_ZONES = ["Zone A", "Zone B", "Zone C"]
