"""Loads structured mining data from JSON files.

All tools read through this module so data access is centralized and easy to
swap for a database later.
"""

import json
import os

from .config import DATA_DIR


def _load(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_gas_readings():
    return _load("gas_readings.json")


def get_equipment():
    return _load("equipment.json")


def get_incidents():
    return _load("incidents.json")
