"""Fixed, offline specification for the draft PhD follow-up."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ("ai_use", "fabrication", "technical_error")
STATES = ("verified", "pending", "confirmed", "cleared", "appeal", "acknowledged")
CONDITIONS = ("clean", "neutral_control") + tuple(
    f"{scenario}_{state}" for scenario in SCENARIOS for state in STATES
)
TASKS = ("quality", "advance")
MODELS = {
    "GPT-5.4 mini": "openai/gpt-5.4-mini",
    "Llama 4 Maverick": "meta-llama/llama-4-maverick",
    "Qwen3-32B": "qwen/qwen3-32b",
    "Gemma 4 31B IT": "google/gemma-4-31b-it",
}
SOURCE_CONDITIONS = {
    "clean": "clean", "neutral_control": "neutral_control",
    "ai_use_pending": "pending", "ai_use_confirmed": "responsible",
    "ai_use_cleared": "cleared", "ai_use_appeal": "exonerated_on_appeal",
    "ai_use_acknowledged": "exonerated_acknowledged",
}
ACKNOWLEDGMENT = (
    " The university also issued a written acknowledgment that its original finding was erroneous.",
    " The university subsequently issued a written acknowledgment that its original finding was erroneous.",
)
PRIMARY_PAIRS = (("cleared", "verified"), ("appeal", "verified"), ("acknowledged", "appeal"))


def load_manifest(path=ROOT / "analysis/phd_followup_conditions.csv"):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 20 or {r["condition"] for r in rows} != set(CONDITIONS):
        raise ValueError("Manifest must contain each of the 20 specified conditions once")
    for row in rows:
        condition = row["condition"]
        if condition in ("clean", "neutral_control"):
            expected = ("shared", condition, "")
        else:
            scenario, state = next((s, t) for s in SCENARIOS for t in STATES if f"{s}_{t}" == condition)
            expected = (scenario, state, f"{scenario}_verified")
        if (row["scenario"], row["state"], row["verification_reference"]) != expected:
            raise ValueError(f"Incorrect scenario/state/reference for {condition}")
        if row["source_condition"] != SOURCE_CONDITIONS.get(condition, ""):
            raise ValueError(f"Incorrect source mapping for {condition}")
    return {r["condition"]: r for r in rows}
