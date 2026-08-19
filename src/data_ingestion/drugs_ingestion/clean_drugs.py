"""
clean_drugs.py
--------------
Cleans the unified Egyptian drug dataset JSON file.

Usage:
    python clean_drugs.py <input_path> <output_path>

Example:
    python clean_drugs.py unified_egyptian_drugs.json cleaned_drugs.json
"""

import json
import re
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ARABIC_FIELDS_TO_REMOVE = {"name_ar", "uses_ar", "warnings_summary_ar"}

TEXT_FIELDS_TO_CLEAN = [
    "name_en",
    "active_ingredients",
    "drug_class",
    "route",
    "manufacturer",
    "uses_en",
    "warnings_summary_en",
]

SAFETY_KEYS = [
    "pregnancy",
    "lactation",
    "hypertension",
    "diabetes",
    "kidney",
    "liver",
    "heart",
]

SAFETY_LABEL_MAP = {
    True: "Caution required",
    False: "No specific warning recorded",
    None: "Insufficient information available; consult a doctor or pharmacist.",
}

SAFETY_KEY_LABELS = {
    "pregnancy": "Pregnancy",
    "lactation": "Lactation/Breastfeeding",
    "hypertension": "High Blood Pressure",
    "diabetes": "Diabetes",
    "kidney": "Kidney Disease",
    "liver": "Liver Disease",
    "heart": "Heart Disease",
}

NULL_SAFETY_REPLACEMENT = (
    "Safety warning information unavailable; consult a doctor or pharmacist."
)

# ---------------------------------------------------------------------------
# Core cleaning functions
# ---------------------------------------------------------------------------


def clean_text(value: Optional[str]) -> Optional[str]:
    """
    Light-touch cleaning of a free-text English field.

    Operations applied (in order):
    1. Return None unchanged.
    2. Strip leading/trailing whitespace.
    3. Collapse internal runs of whitespace to a single space.
    4. Remove stray leading punctuation artifacts (e.g. ': ' at the start).
    5. Collapse multiple consecutive '||' separators into one.
    6. Collapse runs of '.' or ',' into a single instance.
    7. Capitalise the very first character (preserves all-caps tokens like
       drug names / dosages further into the string).

    What is deliberately NOT done:
    - No sentence-level rewriting.
    - No removal of dosage, strength, or formulation tokens.
    - No translation or Arabic removal (handled separately).
    """
    if value is None:
        return None

    text = str(value)

    # Strip surrounding whitespace
    text = text.strip()

    # Collapse internal whitespace
    text = re.sub(r"[ \t]+", " ", text)

    # Remove stray leading colon/punctuation artifacts (e.g. ": text")
    text = re.sub(r"^[:\-–—,;.]+\s*", "", text)

    # Normalise multiple '||' separators
    text = re.sub(r"(\|\|)+", "||", text)

    # Strip whitespace around '||'
    text = re.sub(r"\s*\|\|\s*", " || ", text)

    # Collapse duplicate sentence-ending punctuation
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r",{2,}", ",", text)

    # Trim again after internal changes
    text = text.strip()

    # Capitalise the leading character only (leave the rest untouched)
    if text:
        text = text[0].upper() + text[1:]

    return text if text else None


def normalize_ingredients(value: Optional[str]) -> Optional[str]:
    """
    Normalise the `active_ingredients` field.

    Rules:
    - Apply clean_text first.
    - Ensure exactly one space on each side of '+' separators.
    - Upper-case the entire string (ingredient lists are conventionally
      written in uppercase in this dataset; dosage tokens like '500 MG'
      are preserved).
    """
    if value is None:
        return None

    text = clean_text(value)
    if text is None:
        return None

    # Normalise spacing around '+' (ingredient delimiter)
    text = re.sub(r"\s*\+\s*", " + ", text)

    # Collapse any double spaces that may have been introduced
    text = re.sub(r" {2,}", " ", text)

    # Preserve the dataset convention: ingredients in UPPER CASE
    text = text.upper()

    return text.strip() if text.strip() else None


def transform_safety_warnings(obj: dict) -> dict:
    """
    Convert a safety_warnings dict from boolean/null values to
    human-readable strings.

    Input:  {"pregnancy": true, "kidney": false, "liver": null, ...}
    Output: {"pregnancy": "Caution required",
             "kidney": "No specific warning recorded",
             "liver": "Insufficient information available; ...", ...}

    Keys not in SAFETY_KEYS are passed through unchanged.
    """
    result = {}
    for key, val in obj.items():
        if key in SAFETY_KEYS:
            result[key] = SAFETY_LABEL_MAP.get(val, SAFETY_LABEL_MAP[None])
        else:
            result[key] = val
    return result


def generate_warning_summary(safety_warnings: dict) -> str:
    """
    Build a concise English summary sentence from an already-transformed
    safety_warnings dict (i.e. after `transform_safety_warnings` has run).

    Only mentions conditions that carry an active caution ("Caution required").
    Falls back to a generic "no special warnings" sentence when none are active.

    No external medical knowledge is added.
    """
    caution_labels = [
        SAFETY_KEY_LABELS[k]
        for k in SAFETY_KEYS
        if k in safety_warnings and safety_warnings[k] == "Caution required"
    ]

    if caution_labels:
        conditions = ", ".join(caution_labels)
        return (
            f"Caution or warning advised under medical supervision for: {conditions}."
        )
    else:
        return "No special warnings recorded for the monitored conditions. Always consult a doctor or pharmacist."


# ---------------------------------------------------------------------------
# Record-level processing
# ---------------------------------------------------------------------------


def process_record(record: dict) -> dict:
    """
    Apply all cleaning and transformation rules to a single drug record.

    Order of operations:
    1. Remove Arabic fields.
    2. Clean free-text English fields.
    3. Normalise active_ingredients.
    4. Transform safety_warnings (bool/null → string).
    5. Handle or generate warnings_summary_en.
    6. Preserve metadata fields unchanged.
    """
    cleaned: dict = {}

    for key, value in record.items():

        # ── 1. Drop Arabic fields ──────────────────────────────────────────
        if key in ARABIC_FIELDS_TO_REMOVE:
            continue

        # ── 2 & 3. Clean text fields ──────────────────────────────────────
        elif key == "active_ingredients":
            cleaned[key] = normalize_ingredients(value)

        elif key in TEXT_FIELDS_TO_CLEAN and key != "warnings_summary_en":
            # warnings_summary_en handled separately below
            cleaned[key] = clean_text(value)

        # ── 4. Transform safety_warnings ──────────────────────────────────
        elif key == "safety_warnings":
            if value is None:
                cleaned[key] = NULL_SAFETY_REPLACEMENT
            elif isinstance(value, dict):
                cleaned[key] = transform_safety_warnings(value)
            else:
                # Unexpected type — preserve as-is to avoid data loss
                cleaned[key] = value

        # ── 5. Handle warnings_summary_en ─────────────────────────────────
        elif key == "warnings_summary_en":
            # Deferred: handled after safety_warnings is resolved (see below)
            pass  # placeholder so we can post-process

        # ── 6. Preserve metadata and all other fields unchanged ───────────
        else:
            cleaned[key] = value

    # ── 5. Post-process warnings_summary_en ───────────────────────────────
    existing_summary = record.get("warnings_summary_en")
    resolved_safety = cleaned.get("safety_warnings")

    if existing_summary is not None:
        # Field exists: light clean only, no rewriting
        cleaned["warnings_summary_en"] = clean_text(existing_summary)
    else:
        # Field is null: generate from safety_warnings if available
        if isinstance(resolved_safety, dict):
            cleaned["warnings_summary_en"] = generate_warning_summary(resolved_safety)
        elif isinstance(resolved_safety, str):
            # safety_warnings itself was null → use its replacement message
            cleaned["warnings_summary_en"] = resolved_safety
        else:
            cleaned["warnings_summary_en"] = None

    return cleaned


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_output(original: list, cleaned: list) -> None:
    """
    Lightweight post-processing validation. Raises ValueError if any
    critical invariant is violated.
    """
    if len(original) != len(cleaned):
        raise ValueError(
            f"Record count mismatch: input={len(original)}, output={len(cleaned)}"
        )

    for idx, (orig, clean) in enumerate(zip(original, cleaned)):
        # Arabic fields must be absent
        for ar_field in ARABIC_FIELDS_TO_REMOVE:
            if ar_field in clean:
                raise ValueError(
                    f"Record {idx}: Arabic field '{ar_field}' was not removed."
                )

        # Metadata must be preserved
        for meta_field in ("slug", "barcode", "sources"):
            if meta_field in orig and orig[meta_field] != clean.get(meta_field):
                raise ValueError(
                    f"Record {idx}: metadata field '{meta_field}' was modified."
                )

    logger.info("Validation passed: %d records verified.", len(cleaned))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(input_path: str, output_path: str) -> None:
    logger.info("Loading input file: %s", input_path)

    with open(input_path, "r", encoding="utf-8") as f:
        data: list = json.load(f)

    if not isinstance(data, list):
        raise TypeError(
            "Expected a JSON array at the top level, but got: "
            + type(data).__name__
        )

    logger.info("Loaded %d records. Starting cleaning …", len(data))

    cleaned = [process_record(r) for r in data]

    logger.info("Cleaning complete. Running validation …")
    validate_output(data, cleaned)

    logger.info("Writing output to: %s", output_path)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    logger.info(
        "Done. %d records written to '%s'.", len(cleaned), output_path
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    RAW_DRUGS_DIR = PROJECT_ROOT / "data" / "raw" / "Drugs"

    parser = argparse.ArgumentParser(description="Cleans the unified Egyptian drug dataset JSON file.")
    parser.add_argument(
        "--input", "-i",
        default=str(RAW_DRUGS_DIR / "unified_egyptian_drugs.json"),
        help="Path to unified_egyptian_drugs.json"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(RAW_DRUGS_DIR / "cleaned_drugs.json"),
        help="Output path for cleaned JSON"
    )
    args = parser.parse_args()

    main(args.input, args.output)
