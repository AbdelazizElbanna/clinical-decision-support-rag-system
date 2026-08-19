"""
chunk_eczema.py
───────────────
Schema-aware chunking for the Atopic Dermatitis / Eczema disease JSON.

Transforms the structured eczema JSON into embedding-ready chunk objects
using semantic/schema boundaries rather than character or token splitting.

Usage:
    python chunk_eczema.py
    python chunk_eczema.py --input <path> --output <path>

Defaults:
    input:  data/raw/diseases/Eczema Atopic Dermatitis/eczema_atopic_dermatitis.json
    output: data/Chunked_Data/diseases_chunked/eczema_atopic_dermatitis_chunked.json
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Optional

# ──────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

CONDITION_ID = "eczema_atopic_dermatitis"
CONDITION_NAME = "Atopic Dermatitis"

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_INPUT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "diseases"
    / "Eczema Atopic Dermatitis"
    / "eczema_atopic_dermatitis.json"
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "Chunked_Data"
    / "diseases_chunked"
    / "eczema_atopic_dermatitis_chunked.json"
)

# ──────────────────────────────────────────────────────────────────────
# Source formatting helpers
# ──────────────────────────────────────────────────────────────────────


def _format_source_text(source: Optional[dict], source_url: Optional[str]) -> str:
    """Build a readable source attribution block."""
    parts: list[str] = []
    if source and isinstance(source, dict):
        page = source.get("page_title", "")
        if page:
            parts.append(f"Source: American Academy of Dermatology (AAD)")
            parts.append(f"Page: {page}")
    if source_url:
        parts.append(f"Source URL: {source_url}")
    return "\n".join(parts)


def _serialize_value(value: Any, indent: int = 0) -> str:
    """Recursively serialize a JSON value into readable plain text."""
    prefix = "  " * indent
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return "N/A"
    if isinstance(value, list):
        lines: list[str] = []
        for item in value:
            if isinstance(item, dict):
                lines.append(_serialize_value(item, indent))
            else:
                lines.append(f"{prefix}- {item}")
        return "\n".join(lines)
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            if k in ("source", "source_url"):
                continue
            label = k.replace("_", " ").title()
            if isinstance(v, (dict, list)):
                lines.append(f"{prefix}{label}:")
                lines.append(_serialize_value(v, indent + 1))
            else:
                lines.append(f"{prefix}{label}: {_serialize_value(v)}")
        return "\n".join(lines)
    return str(value)


# ──────────────────────────────────────────────────────────────────────
# Chunk builder
# ──────────────────────────────────────────────────────────────────────


def _make_chunk(
    chunk_id: str,
    section: str,
    subsection: Optional[str],
    chunk_type: str,
    content: Any,
    text: str,
    source: Optional[dict] = None,
    source_url: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "chunk_id": chunk_id,
        "condition_id": CONDITION_ID,
        "condition": CONDITION_NAME,
        "section": section,
        "subsection": subsection,
        "chunk_type": chunk_type,
        "source": source,
        "source_url": source_url,
        "content": content,
        "text": text,
    }


def _build_text_header(section: str, subsection: Optional[str] = None) -> str:
    header = f"Condition: {CONDITION_NAME}\nSection: {section}"
    if subsection:
        header += f"\nSubsection: {subsection}"
    return header


def _content_without_source(obj: Any) -> Any:
    """Deep-copy a dict/list removing source and source_url keys at top level."""
    if isinstance(obj, dict):
        return {k: v for k, v in obj.items() if k not in ("source", "source_url")}
    return obj


# ──────────────────────────────────────────────────────────────────────
# Section chunkers
# ──────────────────────────────────────────────────────────────────────


def chunk_overview(data: dict) -> list[dict]:
    overview = data["overview"]
    content = _content_without_source(overview)
    header = _build_text_header("Overview")
    body = _serialize_value(content)
    source_block = _format_source_text(overview.get("source"), overview.get("source_url"))
    text = f"{header}\n\n{body}\n\n{source_block}"
    return [_make_chunk(
        "eczema_overview", "Overview", None, "object",
        content, text,
        overview.get("source"), overview.get("source_url"),
    )]


def chunk_core_symptoms(data: dict) -> list[dict]:
    symptoms_section = data["symptoms"]
    core = symptoms_section["core_symptoms"]
    source = symptoms_section.get("source")
    source_url = symptoms_section.get("source_url")
    chunks = []
    for idx, symptom in enumerate(core, start=1):
        header = _build_text_header("Symptoms", "Core Symptoms")
        body = _serialize_value(symptom)
        source_block = _format_source_text(source, source_url)
        text = f"{header}\n\n{body}\n\n{source_block}"
        chunks.append(_make_chunk(
            f"eczema_core_symptom_{idx:02d}", "Symptoms", "Core Symptoms",
            "array_item", symptom, text, source, source_url,
        ))
    return chunks


def chunk_age_variations(data: dict) -> list[dict]:
    symptoms_section = data["symptoms"]
    age_vars = symptoms_section["age_variations"]
    source = symptoms_section.get("source")
    source_url = symptoms_section.get("source_url")

    mapping = [
        ("infants_and_babies_under_2", "Infants and Babies (Under 2)", "eczema_age_variation_infants"),
        ("children_and_adolescents_2_to_puberty", "Children and Adolescents (2 to Puberty)", "eczema_age_variation_children_adolescents"),
        ("adults", "Adults", "eczema_age_variation_adults"),
    ]
    chunks = []
    for key, label, chunk_id in mapping:
        obj = age_vars[key]
        subsection = f"Age Variation - {label}"
        header = _build_text_header("Symptoms", subsection)
        body = _serialize_value(obj)
        source_block = _format_source_text(source, source_url)
        text = f"{header}\n\n{body}\n\n{source_block}"
        chunks.append(_make_chunk(
            chunk_id, "Symptoms", subsection, "object",
            obj, text, source, source_url,
        ))
    return chunks


def chunk_skin_tone_variations(data: dict) -> list[dict]:
    symptoms_section = data["symptoms"]
    stv = symptoms_section["skin_tone_variations"]
    source = symptoms_section.get("source")
    source_url = symptoms_section.get("source_url")
    header = _build_text_header("Symptoms", "Skin Tone Variations")
    body = _serialize_value(stv)
    source_block = _format_source_text(source, source_url)
    text = f"{header}\n\n{body}\n\n{source_block}"
    return [_make_chunk(
        "eczema_skin_tone_variations", "Symptoms", "Skin Tone Variations",
        "object", stv, text, source, source_url,
    )]


def chunk_causes(data: dict) -> list[dict]:
    causes_section = data["causes"]
    factors = causes_section["factors"]
    source = causes_section.get("source")
    source_url = causes_section.get("source_url")
    chunks = []
    for idx, factor in enumerate(factors, start=1):
        header = _build_text_header("Causes", "Cause Factor")
        body = _serialize_value(factor)
        source_block = _format_source_text(source, source_url)
        text = f"{header}\n\n{body}\n\n{source_block}"
        chunks.append(_make_chunk(
            f"eczema_cause_{idx:02d}", "Causes", "Cause Factor",
            "array_item", factor, text, source, source_url,
        ))
    return chunks


def chunk_risk_factors(data: dict) -> list[dict]:
    rf_section = data["risk_factors"]
    items = rf_section["list"]
    source = rf_section.get("source")
    source_url = rf_section.get("source_url")
    chunks = []
    for idx, item in enumerate(items, start=1):
        header = _build_text_header("Risk Factors")
        source_block = _format_source_text(source, source_url)
        text = f"{header}\n\n{item}\n\n{source_block}"
        chunks.append(_make_chunk(
            f"eczema_risk_factor_{idx:02d}", "Risk Factors", None,
            "array_item", item, text, source, source_url,
        ))
    return chunks


def chunk_triggers(data: dict) -> list[dict]:
    triggers = data["triggers"]
    chunks = []
    for trigger in triggers:
        trig_id = trigger.get("id", "")
        chunk_id = f"eczema_trigger_{trig_id}" if trig_id else f"eczema_trigger_{trigger['name'].lower().replace(' ', '_')}"
        source = trigger.get("source")
        source_url = trigger.get("source_url")
        content = _content_without_source(trigger)
        header = _build_text_header("Triggers", "Trigger")
        body = _serialize_value(content)
        source_block = _format_source_text(source, source_url)
        text = f"{header}\n\n{body}\n\n{source_block}"
        chunks.append(_make_chunk(
            chunk_id, "Triggers", "Trigger", "array_item",
            content, text, source, source_url,
        ))
    return chunks


def chunk_environmental_factors(data: dict) -> list[dict]:
    factors = data["environmental_factors"]
    chunks = []
    for idx, factor in enumerate(factors, start=1):
        source = factor.get("source")
        source_url = factor.get("source_url")
        content = _content_without_source(factor)
        header = _build_text_header("Environmental Factors", "Environmental Factor")
        body = _serialize_value(content)
        source_block = _format_source_text(source, source_url)
        text = f"{header}\n\n{body}\n\n{source_block}"
        chunks.append(_make_chunk(
            f"eczema_environmental_factor_{idx:02d}",
            "Environmental Factors", "Environmental Factor", "array_item",
            content, text, source, source_url,
        ))
    return chunks


def chunk_skin_care(data: dict) -> list[dict]:
    sc = data["skin_care_and_self_care"]
    content = _content_without_source(sc)
    source = sc.get("source")
    source_url = sc.get("source_url")
    header = _build_text_header("Skin Care and Self Care")
    body = _serialize_value(content)
    source_block = _format_source_text(source, source_url)
    text = f"{header}\n\n{body}\n\n{source_block}"
    return [_make_chunk(
        "eczema_skin_care_and_self_care", "Skin Care and Self Care", None,
        "object", content, text, source, source_url,
    )]


def chunk_flare_ups(data: dict) -> list[dict]:
    fu = data["flare_ups_management"]
    content = _content_without_source(fu)
    source = fu.get("source")
    source_url = fu.get("source_url")
    header = _build_text_header("Flare-Up Management")
    body = _serialize_value(content)
    source_block = _format_source_text(source, source_url)
    text = f"{header}\n\n{body}\n\n{source_block}"
    return [_make_chunk(
        "eczema_flare_ups_management", "Flare-Up Management", None,
        "object", content, text, source, source_url,
    )]


def chunk_red_flags(data: dict) -> list[dict]:
    rf = data["red_flags_and_warning_signs"]
    signs = rf["signs"]
    source = rf.get("source")
    source_url = rf.get("source_url")
    chunks = []
    for idx, sign in enumerate(signs, start=1):
        header = _build_text_header("Red Flags and Warning Signs", "Warning Sign")
        body = _serialize_value(sign)
        source_block = _format_source_text(source, source_url)
        text = f"{header}\n\n{body}\n\n{source_block}"
        chunks.append(_make_chunk(
            f"eczema_red_flag_{idx:02d}",
            "Red Flags and Warning Signs", "Warning Sign", "array_item",
            sign, text, source, source_url,
        ))
    return chunks


def chunk_when_to_see_doctor(data: dict) -> list[dict]:
    wtsd = data["when_to_see_doctor"]
    recs = wtsd["recommendations"]
    source = wtsd.get("source")
    source_url = wtsd.get("source_url")
    chunks = []
    for idx, rec in enumerate(recs, start=1):
        header = _build_text_header("When to See Doctor")
        source_block = _format_source_text(source, source_url)
        text = f"{header}\n\n{rec}\n\n{source_block}"
        chunks.append(_make_chunk(
            f"eczema_when_to_see_doctor_{idx:02d}",
            "When to See Doctor", None, "array_item",
            rec, text, source, source_url,
        ))
    return chunks


def chunk_related_conditions(data: dict) -> list[dict]:
    rc = data["related_conditions"]
    conditions = rc["conditions"]
    source = rc.get("source")
    source_url = rc.get("source_url")
    chunks = []
    for idx, cond in enumerate(conditions, start=1):
        header = _build_text_header("Related Conditions", "Related Condition")
        body = _serialize_value(cond)
        source_block = _format_source_text(source, source_url)
        text = f"{header}\n\n{body}\n\n{source_block}"
        chunks.append(_make_chunk(
            f"eczema_related_condition_{idx:02d}",
            "Related Conditions", "Related Condition", "array_item",
            cond, text, source, source_url,
        ))
    return chunks


def chunk_medications(data: dict) -> list[dict]:
    meds = data["medications_and_treatments"]
    source = meds.get("source")
    source_url = meds.get("source_url")
    chunks = []

    # A. Topical therapies
    for idx, therapy in enumerate(meds["topical_therapies"], start=1):
        header = _build_text_header("Medications and Treatments", "Topical Therapy")
        body = _serialize_value(therapy)
        source_block = _format_source_text(source, source_url)
        text = f"{header}\n\n{body}\n\n{source_block}"
        chunks.append(_make_chunk(
            f"eczema_topical_therapy_{idx:02d}",
            "Medications and Treatments", "Topical Therapy", "array_item",
            therapy, text, source, source_url,
        ))

    # B. Phototherapy
    photo = meds["phototherapy_light_therapy"]
    header = _build_text_header("Medications and Treatments", "Phototherapy / Light Therapy")
    body = _serialize_value(photo)
    source_block = _format_source_text(source, source_url)
    text = f"{header}\n\n{body}\n\n{source_block}"
    chunks.append(_make_chunk(
        "eczema_phototherapy",
        "Medications and Treatments", "Phototherapy / Light Therapy", "object",
        photo, text, source, source_url,
    ))

    # C. Systemic therapies / biologics / JAK inhibitors
    for idx, therapy in enumerate(meds["systemic_therapies_biologics_and_jak_inhibitors"], start=1):
        header = _build_text_header("Medications and Treatments", "Systemic Therapy / Biologic / JAK Inhibitor")
        body = _serialize_value(therapy)
        source_block = _format_source_text(source, source_url)
        text = f"{header}\n\n{body}\n\n{source_block}"
        chunks.append(_make_chunk(
            f"eczema_systemic_therapy_{idx:02d}",
            "Medications and Treatments", "Systemic Therapy / Biologic / JAK Inhibitor",
            "array_item", therapy, text, source, source_url,
        ))

    # D. Supportive / infection treatments
    for idx, treatment in enumerate(meds["supportive_and_infection_treatments"], start=1):
        header = _build_text_header("Medications and Treatments", "Supportive / Infection Treatment")
        body = _serialize_value(treatment)
        source_block = _format_source_text(source, source_url)
        text = f"{header}\n\n{body}\n\n{source_block}"
        chunks.append(_make_chunk(
            f"eczema_supportive_treatment_{idx:02d}",
            "Medications and Treatments", "Supportive / Infection Treatment",
            "array_item", treatment, text, source, source_url,
        ))

    return chunks


# ──────────────────────────────────────────────────────────────────────
# Pipeline
# ──────────────────────────────────────────────────────────────────────

SECTION_CHUNKERS = [
    ("Overview", chunk_overview),
    ("Core Symptoms", chunk_core_symptoms),
    ("Age Variations", chunk_age_variations),
    ("Skin Tone Variations", chunk_skin_tone_variations),
    ("Causes", chunk_causes),
    ("Risk Factors", chunk_risk_factors),
    ("Triggers", chunk_triggers),
    ("Environmental Factors", chunk_environmental_factors),
    ("Skin Care and Self Care", chunk_skin_care),
    ("Flare-Up Management", chunk_flare_ups),
    ("Red Flags and Warning Signs", chunk_red_flags),
    ("When to See Doctor", chunk_when_to_see_doctor),
    ("Related Conditions", chunk_related_conditions),
    ("Medications and Treatments", chunk_medications),
]


def process_eczema(data: dict) -> list[dict]:
    all_chunks: list[dict] = []
    report: list[tuple[str, int]] = []

    for label, chunker in SECTION_CHUNKERS:
        section_chunks = chunker(data)
        report.append((label, len(section_chunks)))
        all_chunks.extend(section_chunks)

    # Sub-report for medications
    med_chunks = [c for c in all_chunks if c["section"] == "Medications and Treatments"]
    topical = sum(1 for c in med_chunks if c["subsection"] == "Topical Therapy")
    photo = sum(1 for c in med_chunks if "Phototherapy" in (c["subsection"] or ""))
    systemic = sum(1 for c in med_chunks if "Systemic" in (c["subsection"] or ""))
    supportive = sum(1 for c in med_chunks if "Supportive" in (c["subsection"] or ""))

    # Print report
    logger.info("")
    logger.info("Atopic Dermatitis Chunking Complete")
    logger.info("")
    for label, count in report:
        if label == "Medications and Treatments":
            logger.info("  Topical Therapies: %d", topical)
            logger.info("  Phototherapy: %d", photo)
            logger.info("  Systemic Therapies: %d", systemic)
            logger.info("  Supportive/Infection Treatments: %d", supportive)
        else:
            logger.info("  %s: %d", label, count)
    logger.info("")
    logger.info("  Total: %d", len(all_chunks))
    logger.info("")

    return all_chunks


# ──────────────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────────────


def validate_chunks(data: dict, chunks: list[dict]) -> None:
    logger.info("─" * 56)
    logger.info("  Validation Report")
    logger.info("─" * 56)

    errors = 0

    # 1. Condition checks
    if data.get("condition_id") != CONDITION_ID:
        logger.error("  condition_id mismatch: %s", data.get("condition_id"))
        errors += 1
    else:
        logger.info("  ✅ condition_id matches")

    if data.get("name_en") != CONDITION_NAME:
        logger.error("  name_en mismatch: %s", data.get("name_en"))
        errors += 1
    else:
        logger.info("  ✅ condition name matches")

    # 2. Unique chunk IDs
    ids = [c["chunk_id"] for c in chunks]
    id_counts = Counter(ids)
    dupes = {k: v for k, v in id_counts.items() if v > 1}
    if dupes:
        logger.error("  Duplicate chunk_ids: %s", dupes)
        errors += 1
    else:
        logger.info("  ✅ All %d chunk_ids are unique", len(ids))

    # 3. Every chunk has required fields
    required = ["chunk_id", "condition_id", "condition", "section", "chunk_type", "content", "text"]
    missing_fields = []
    for c in chunks:
        for field in required:
            if field not in c or (field == "text" and not c[field]):
                missing_fields.append((c["chunk_id"], field))
    if missing_fields:
        logger.error("  Missing fields: %s", missing_fields[:10])
        errors += 1
    else:
        logger.info("  ✅ All chunks have required fields")

    # 4. Condition context in text
    no_context = [c for c in chunks if CONDITION_NAME not in c["text"]]
    if no_context:
        logger.error("  %d chunks missing condition context in text", len(no_context))
        errors += 1
    else:
        logger.info("  ✅ All chunks contain condition context in text")

    # 5. Section context in text
    no_section = [c for c in chunks if c["section"] not in c["text"]]
    if no_section:
        logger.error("  %d chunks missing section context in text", len(no_section))
        errors += 1
    else:
        logger.info("  ✅ All chunks contain section context in text")

    # 6. Source info where available
    chunks_with_source = [c for c in chunks if c.get("source") is not None or c.get("source_url") is not None]
    logger.info("  📊 %d / %d chunks have source information", len(chunks_with_source), len(chunks))

    # 7. Expected section counts
    expected_counts = {
        "Overview": 1,
        "Core Symptoms": len(data["symptoms"]["core_symptoms"]),
        "Age Variations": 3,
        "Skin Tone Variations": 1,
        "Causes": len(data["causes"]["factors"]),
        "Risk Factors": len(data["risk_factors"]["list"]),
        "Triggers": len(data["triggers"]),
        "Environmental Factors": len(data["environmental_factors"]),
        "Skin Care and Self Care": 1,
        "Flare-Up Management": 1,
        "Red Flags and Warning Signs": len(data["red_flags_and_warning_signs"]["signs"]),
        "When to See Doctor": len(data["when_to_see_doctor"]["recommendations"]),
        "Related Conditions": len(data["related_conditions"]["conditions"]),
    }

    section_label_map = {
        "Core Symptoms": "Symptoms",
        "Age Variations": "Symptoms",
        "Skin Tone Variations": "Symptoms",
        "Red Flags and Warning Signs": "Red Flags and Warning Signs",
    }

    for label, chunker in SECTION_CHUNKERS:
        if label == "Medications and Treatments":
            continue
        actual_section = section_label_map.get(label, label)
        if label in ("Core Symptoms", "Age Variations", "Skin Tone Variations"):
            subsection_map = {
                "Core Symptoms": "Core Symptoms",
                "Age Variations": None,
                "Skin Tone Variations": "Skin Tone Variations",
            }
            if label == "Age Variations":
                actual_count = sum(1 for c in chunks if c["section"] == "Symptoms" and c.get("subsection", "").startswith("Age Variation"))
            else:
                sub = subsection_map[label]
                actual_count = sum(1 for c in chunks if c["section"] == "Symptoms" and c.get("subsection") == sub)
        else:
            actual_count = sum(1 for c in chunks if c["section"] == actual_section)

        expected = expected_counts.get(label, 0)
        if actual_count != expected:
            logger.error("  %s: expected %d, got %d", label, expected, actual_count)
            errors += 1
        else:
            logger.info("  ✅ %s: %d chunks (correct)", label, actual_count)

    if errors:
        logger.error("  ❌ %d validation error(s) found", errors)
    else:
        logger.info("  ✅ All validations passed")
    logger.info("─" * 56)


# ──────────────────────────────────────────────────────────────────────
# I/O
# ──────────────────────────────────────────────────────────────────────


def load_data(input_path: Path) -> dict:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise TypeError(f"Expected a JSON object, got: {type(data).__name__}")
    logger.info("Loaded disease JSON from %s", input_path.name)
    return data


def save_chunks(chunks: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("Saved %d chunks to %s (%.2f MB)", len(chunks), output_path.name, size_mb)


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────


def main(input_path: str | Path, output_path: str | Path) -> None:
    t0 = time.perf_counter()
    input_path = Path(input_path)
    output_path = Path(output_path)

    # Load (keep original for integrity check)
    data = load_data(input_path)
    original_json = json.dumps(data, ensure_ascii=False, sort_keys=True)

    # Process
    chunks = process_eczema(data)

    # Validate input not modified
    post_json = json.dumps(data, ensure_ascii=False, sort_keys=True)
    if original_json != post_json:
        logger.error("Input JSON was modified during processing!")
        sys.exit(1)
    else:
        logger.info("✅ Input JSON integrity preserved")

    # Validate output
    validate_chunks(data, chunks)

    # Verify output is valid JSON by round-tripping
    try:
        json.loads(json.dumps(chunks, ensure_ascii=False))
        logger.info("✅ Output is valid JSON")
    except (json.JSONDecodeError, TypeError) as exc:
        logger.error("Output is not valid JSON: %s", exc)
        sys.exit(1)

    # Save
    save_chunks(chunks, output_path)

    elapsed = time.perf_counter() - t0
    logger.info("Completed in %.2f seconds.", elapsed)


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Schema-aware chunking for the Atopic Dermatitis / Eczema disease JSON."
    )
    parser.add_argument(
        "--input", "-i",
        default=str(DEFAULT_INPUT),
        help="Path to the eczema disease JSON file.",
    )
    parser.add_argument(
        "--output", "-o",
        default=str(DEFAULT_OUTPUT),
        help="Path to write the chunked output JSON file.",
    )
    args = parser.parse_args()
    main(args.input, args.output)
