"""
Soil health ingestion.

There is no live public API for Soil Health Card data — it's distributed as
bulk state-wise downloads (soilhealth.dac.gov.in). Real pipeline: download
the Sehore district CSV once, load it here, look up by village/plot code.

This module is built so that swapping the fallback for a real CSV load is a
one-line change (see load_dataset()) — nothing else in the app needs to
change.
"""
import csv
import os

DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "soil_health_sehore.csv")

_dataset_cache = None


def load_dataset() -> dict:
    """
    Loads the soil dataset into memory, keyed by plot_code.
    Expected CSV columns: plot_code,nitrogen_kg_ha,phosphorus_kg_ha,
    potassium_kg_ha,ph,organic_carbon_pct,last_tested
    """
    global _dataset_cache
    if _dataset_cache is not None:
        return _dataset_cache

    _dataset_cache = {}
    if not os.path.exists(DATASET_PATH):
        return _dataset_cache

    with open(DATASET_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _dataset_cache[row["plot_code"]] = row
    return _dataset_cache


def get_all_plots() -> list:
    """
    Returns every plot in the registry with its coordinates and block —
    used by the policy dashboard to aggregate across the whole district
    without needing a hardcoded plot list in app.py.
    """
    dataset = load_dataset()
    return [
        {
            "plot_code": code,
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "block": row.get("block", "Unknown"),
        }
        for code, row in dataset.items()
    ]


def get_soil_data(plot_code: str) -> dict:
    dataset = load_dataset()
    row = dataset.get(plot_code)

    if not row:
        return _fallback("plot_not_found_in_dataset")

    def classify_nitrogen(val):
        val = float(val)
        if val < 280:
            return "low"
        if val < 560:
            return "medium"
        return "high"

    return {
        "status": "ok",
        "nitrogen_kg_ha": float(row["nitrogen_kg_ha"]),
        "nitrogen_level": classify_nitrogen(row["nitrogen_kg_ha"]),
        "phosphorus_kg_ha": float(row["phosphorus_kg_ha"]),
        "potassium_kg_ha": float(row["potassium_kg_ha"]),
        "ph": float(row["ph"]),
        "organic_carbon_pct": float(row["organic_carbon_pct"]),
        "last_tested": row["last_tested"],
    }


def _fallback(reason: str) -> dict:
    return {
        "status": "unavailable",
        "reason": reason,
        "nitrogen_kg_ha": None,
        "nitrogen_level": None,
        "phosphorus_kg_ha": None,
        "potassium_kg_ha": None,
        "ph": None,
        "organic_carbon_pct": None,
        "last_tested": None,
    }
