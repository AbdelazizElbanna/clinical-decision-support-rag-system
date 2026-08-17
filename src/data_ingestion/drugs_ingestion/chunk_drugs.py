"""
chunk_drugs.py
──────────────
Transforms cleaned drug JSON records into LangChain Documents
ready for embedding.

Strategy: Object-Level + Contextual Chunking
    1 JSON drug object  →  1 LangChain Document  →  1 embedding

Usage:
    python chunk_drugs.py --input <cleaned.json> --output <documents.json>

Example:
    python chunk_drugs.py \
        --input  ../../data/Drugs/filtered_skin_drugs.json \
        --output ../../data/Drugs/drug_documents.json

Design rationale (see § at the bottom of this file):
    • Each drug is an atomic semantic unit — splitting would lose context.
    • Semantic fields (name, ingredients, uses, warnings) go into page_content
      for dense retrieval.
    • Identifiers and provenance (slug, barcode, sources) go into metadata
      for filtering, tracing, and display.
    • Traditional recursive / character-based chunking is inappropriate here
      because the data is already structured at the object level.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from langchain_core.documents import Document

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

# The string produced by clean_drugs.py when the entire safety_warnings
# field was originally null.
UNAVAILABLE_SAFETY_MARKER = (
    "Safety warning information unavailable; consult a doctor or pharmacist."
)

# Human-readable labels for structured safety warning keys.
SAFETY_KEY_LABELS: dict[str, str] = {
    "pregnancy": "Pregnancy",
    "lactation": "Lactation",
    "hypertension": "Hypertension",
    "diabetes": "Diabetes",
    "kidney": "Kidney",
    "liver": "Liver",
    "heart": "Heart",
}

# Ordered keys — consistent rendering across every document.
SAFETY_KEY_ORDER: list[str] = [
    "pregnancy",
    "lactation",
    "hypertension",
    "diabetes",
    "kidney",
    "liver",
    "heart",
]


# ──────────────────────────────────────────────────────────────────────
# Helper: title-case a field value for readable embedding text
# ──────────────────────────────────────────────────────────────────────

def _title_case(value: str) -> str:
    """
    Convert an ALL-CAPS or mixed-case string to Title Case while
    preserving parenthesised content and common abbreviations.

    Used for rendering ingredients, drug class, route, manufacturer
    inside page_content so the embedding model sees natural language
    rather than raw uppercase tokens.

    Examples:
        "CHLORPHENIRAMINE + PARACETAMOL(ACETAMINOPHEN)"
            → "Chlorpheniramine + Paracetamol (Acetaminophen)"
        "ORAL.SOLID" → "Oral Solid"
        "HIKMA PHARMA" → "Hikma Pharma"
    """
    # Replace dots used as category separators with spaces
    text = value.replace(".", " ").strip()
    # Normalise whitespace
    text = " ".join(text.split())
    # Title-case
    text = text.title()
    # Fix common parenthesised content spacing: "Paracetamol(Acet…" → "Paracetamol (Acet…"
    import re
    text = re.sub(r"(\w)\(", r"\1 (", text)
    return text


# ──────────────────────────────────────────────────────────────────────
# Core functions
# ──────────────────────────────────────────────────────────────────────

def load_data(input_path: str | Path) -> list[dict[str, Any]]:
    """Load and return the list of drug records from a JSON file."""
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise TypeError(
            f"Expected a JSON array at the top level, got: {type(data).__name__}"
        )

    logger.info("Loaded %d records from %s", len(data), path.name)
    return data


def _format_safety_warnings_dict(sw: dict[str, str]) -> str:
    """
    Render a structured safety_warnings dict as multi-line text.

    Both positive ("Caution required") and negative
    ("No specific warning recorded") states are preserved because
    the absence of a warning is semantically different from missing
    information.
    """
    lines: list[str] = []
    for key in SAFETY_KEY_ORDER:
        if key in sw:
            label = SAFETY_KEY_LABELS.get(key, key.title())
            lines.append(f"  {label}: {sw[key]}")
    # Include any extra keys not in the canonical list
    for key, val in sw.items():
        if key not in SAFETY_KEY_ORDER:
            lines.append(f"  {key.title()}: {val}")
    return "\n".join(lines)


def build_page_content(drug: dict[str, Any]) -> str:
    """
    Construct the semantic text representation of one drug record.

    This text will be sent to the embedding model.  It is designed for
    dense retrieval: a human-readable, section-labelled document that
    carries all the clinical context needed to match a user query to
    the correct drug.

    Fields that are null/empty are silently omitted — no "Unknown" or
    "None" placeholders.
    """
    sections: list[str] = []

    # ── Drug Name ─────────────────────────────────────────────────
    name = drug.get("name_en")
    if name:
        sections.append(f"Drug Name: {name}")

    # ── Active Ingredients ────────────────────────────────────────
    ingredients = drug.get("active_ingredients")
    if ingredients:
        sections.append(f"Active Ingredients: {_title_case(ingredients)}")

    # ── Drug Class ────────────────────────────────────────────────
    drug_class = drug.get("drug_class")
    if drug_class:
        sections.append(f"Drug Class: {_title_case(drug_class)}")

    # ── Route ─────────────────────────────────────────────────────
    route = drug.get("route")
    if route:
        sections.append(f"Route: {_title_case(route)}")

    # ── Manufacturer ──────────────────────────────────────────────
    manufacturer = drug.get("manufacturer")
    if manufacturer:
        sections.append(f"Manufacturer: {_title_case(manufacturer)}")

    # ── Uses ──────────────────────────────────────────────────────
    uses = drug.get("uses_en")
    if uses:
        sections.append(f"Uses: {uses}")

    # ── Safety Warnings ──────────────────────────────────────────
    sw = drug.get("safety_warnings")
    if sw is not None:
        if isinstance(sw, dict):
            # Structured safety data — render each condition
            formatted = _format_safety_warnings_dict(sw)
            sections.append(f"Safety Warnings:\n{formatted}")
        elif isinstance(sw, str):
            # Unavailable marker — represent as a concise availability
            # statement.  The generic "consult a doctor" phrase is NOT
            # a drug-specific fact; we reduce it to "Unavailable" so
            # the embedding is not polluted with boilerplate.
            sections.append("Safety Information: Unavailable")

    # ── Warning Summary ──────────────────────────────────────────
    summary = drug.get("warnings_summary_en")
    if summary:
        # If the summary is the same unavailable marker, skip it —
        # we already represented this above.
        if isinstance(sw, str) and summary == sw:
            pass  # already covered by "Safety Information: Unavailable"
        else:
            sections.append(f"Warning Summary: {summary}")

    return "\n\n".join(sections)


def build_metadata(drug: dict[str, Any]) -> dict[str, Any]:
    """
    Build structured metadata for one drug document.

    Metadata is used for:
        • Filtering (drug_class, route, manufacturer)
        • Exact identification (slug, barcode)
        • Provenance tracing (sources)
        • Display in retrieved results (name_en)
        • Hybrid retrieval (active_ingredients)
        • Safety availability flag for downstream logic
    """
    sw = drug.get("safety_warnings")

    # Determine whether structured safety info is available
    if isinstance(sw, dict):
        safety_available = True
    elif isinstance(sw, str):
        safety_available = False
    else:
        safety_available = False

    metadata: dict[str, Any] = {
        "drug_id": drug.get("slug"),
        "slug": drug.get("slug"),
        "name_en": drug.get("name_en"),
        "active_ingredients": drug.get("active_ingredients"),
        "drug_class": drug.get("drug_class"),
        "route": drug.get("route"),
        "manufacturer": drug.get("manufacturer"),
        "barcode": drug.get("barcode"),
        "sources": drug.get("sources"),
        "safety_info_available": safety_available,
    }

    return metadata


def create_document(drug: dict[str, Any]) -> Document:
    """
    Create a single LangChain Document from one drug record.

    The document ID is the drug's slug — a stable, human-readable
    identifier derived from the drug name.
    """
    page_content = build_page_content(drug)
    metadata = build_metadata(drug)

    doc = Document(
        page_content=page_content,
        metadata=metadata,
        id=drug.get("slug"),
    )
    return doc


# ──────────────────────────────────────────────────────────────────────
# Dataset-level processing
# ──────────────────────────────────────────────────────────────────────

def process_dataset(
    data: list[dict[str, Any]],
) -> tuple[list[Document], list[dict[str, Any]]]:
    """
    Process every record in the dataset.

    Returns:
        documents: list of successfully created Documents
        failures:  list of {"index": int, "slug": str, "error": str}
    """
    documents: list[Document] = []
    failures: list[dict[str, Any]] = []

    for idx, record in enumerate(data):
        try:
            doc = create_document(record)
            documents.append(doc)
        except Exception as exc:
            slug = record.get("slug", f"<unknown-index-{idx}>")
            logger.warning("Record %d (slug=%s) failed: %s", idx, slug, exc)
            failures.append({
                "index": idx,
                "slug": slug,
                "error": str(exc),
            })

    return documents, failures


# ──────────────────────────────────────────────────────────────────────
# Validation & quality checks
# ──────────────────────────────────────────────────────────────────────

def validate_documents(
    data: list[dict[str, Any]],
    documents: list[Document],
    failures: list[dict[str, Any]],
) -> None:
    """
    Run quality checks on the generated documents.

    Checks:
        1. Total count = input count
        2. No missing slugs
        3. Duplicate slug detection (warning, not failure)
        4. No missing name_en
        5. No empty page_content
    """
    total_input = len(data)
    total_docs = len(documents)
    total_fail = len(failures)

    logger.info("─" * 56)
    logger.info("  Validation Report")
    logger.info("─" * 56)
    logger.info("  Input records:       %d", total_input)
    logger.info("  Generated documents: %d", total_docs)
    logger.info("  Failed records:      %d", total_fail)

    # Count check
    if total_docs + total_fail != total_input:
        logger.error(
            "  ❌ Count mismatch: %d + %d ≠ %d",
            total_docs, total_fail, total_input,
        )
    else:
        logger.info("  ✅ Count check passed")

    # Missing slugs
    missing_slug = [d for d in documents if not d.metadata.get("slug")]
    if missing_slug:
        logger.warning(
            "  ⚠️  %d document(s) have missing slug", len(missing_slug)
        )
    else:
        logger.info("  ✅ No missing slugs")

    # Duplicate slugs
    slug_counts = Counter(d.metadata.get("slug") for d in documents)
    duplicates = {s: c for s, c in slug_counts.items() if c > 1}
    if duplicates:
        logger.warning("  ⚠️  %d duplicate slug(s) found:", len(duplicates))
        for slug, count in sorted(
            duplicates.items(), key=lambda x: -x[1]
        )[:20]:
            logger.warning("      %s  (×%d)", slug, count)
        if len(duplicates) > 20:
            logger.warning("      … and %d more", len(duplicates) - 20)
    else:
        logger.info("  ✅ No duplicate slugs")

    # Missing name_en
    missing_name = [
        d for d in documents if not d.metadata.get("name_en")
    ]
    if missing_name:
        logger.warning(
            "  ⚠️  %d document(s) have missing name_en", len(missing_name)
        )
    else:
        logger.info("  ✅ No missing drug names")

    # Empty page_content
    empty_content = [d for d in documents if not d.page_content.strip()]
    if empty_content:
        logger.warning(
            "  ⚠️  %d document(s) have empty page_content",
            len(empty_content),
        )
    else:
        logger.info("  ✅ No empty page_content")

    # Safety info stats
    n_safety_avail = sum(
        1 for d in documents if d.metadata.get("safety_info_available")
    )
    logger.info(
        "  📊 Safety info available: %d / %d (%.1f%%)",
        n_safety_avail,
        total_docs,
        (n_safety_avail / total_docs * 100) if total_docs else 0,
    )

    # Report failures
    if failures:
        logger.warning("  Failed record details:")
        for f in failures[:20]:
            logger.warning(
                "    index=%d  slug=%s  error=%s",
                f["index"], f["slug"], f["error"],
            )
        if len(failures) > 20:
            logger.warning("    … and %d more", len(failures) - 20)

    logger.info("─" * 56)


# ──────────────────────────────────────────────────────────────────────
# Serialisation
# ──────────────────────────────────────────────────────────────────────

def save_documents(documents: list[Document], output_path: str | Path) -> None:
    """
    Serialise the list of Documents to a JSON file.

    Each entry is a dict with "id", "page_content", and "metadata"
    so it can be reloaded later without depending on LangChain's
    serialisation format.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    serialised = []
    for doc in documents:
        serialised.append({
            "id": doc.id,
            "page_content": doc.page_content,
            "metadata": doc.metadata,
        })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(serialised, f, ensure_ascii=False, indent=2)

    size_mb = path.stat().st_size / (1024 * 1024)
    logger.info(
        "Saved %d documents to %s (%.2f MB)", len(serialised), path.name, size_mb
    )


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main(input_path: str, output_path: str) -> None:
    t0 = time.perf_counter()

    # 1. Load
    data = load_data(input_path)

    # 2. Process
    documents, failures = process_dataset(data)

    # 3. Validate
    validate_documents(data, documents, failures)

    # 4. Save
    save_documents(documents, output_path)

    elapsed = time.perf_counter() - t0
    logger.info("Completed in %.2f seconds.", elapsed)


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transform cleaned drug JSON into embedding-ready documents."
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to the cleaned drug JSON file.",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Path to write the output documents JSON file.",
    )
    args = parser.parse_args()

    main(args.input, args.output)


# ══════════════════════════════════════════════════════════════════════
# § Design rationale
# ══════════════════════════════════════════════════════════════════════
#
# 1. ONE DRUG = ONE CHUNK
#    Each drug record is already a self-contained semantic unit.
#    Splitting it (e.g. uses vs. warnings) would scatter context that a
#    user query may need simultaneously ("Is drug X safe for diabetic
#    pregnant patients?").  Keeping the drug whole ensures the retriever
#    returns a single, complete answer source.
#
# 2. SEMANTIC FIELDS IN page_content
#    The embedding model must see the clinical substance: drug name,
#    ingredients, class, uses, and safety warnings.  These are the
#    fields users will query against ("antihistamine for allergies",
#    "contains paracetamol", "safe during pregnancy").  Formatting
#    them as labelled natural-language sections improves cosine
#    similarity with typical user phrasing.
#
# 3. IDENTIFIERS / PROVENANCE IN metadata
#    slug, barcode, and source lists have no semantic retrieval value —
#    nobody queries "find slug abc-123".  But they are essential for
#    post-retrieval filtering, result display, audit trails, and
#    deduplication.  Keeping them in metadata avoids polluting the
#    embedding space.
#
# 4. NO RECURSIVE / CHARACTER-BASED CHUNKING
#    Those strategies exist for unstructured long-form text (PDFs,
#    articles) where document boundaries are unknown.  Here, the JSON
#    objects already define perfect chunk boundaries.  Applying a
#    RecursiveCharacterTextSplitter would either (a) produce one chunk
#    per drug anyway (if chunk_size is large enough) or (b) arbitrarily
#    slice a drug record mid-sentence — both are worse than using the
#    natural object boundary.
#
# 5. DOWNSTREAM EMBEDDING USAGE
#    The output of this script is a list of Documents, each with a
#    unique ID, page_content, and metadata.  The next pipeline stage
#    will:
#      (a) Load these documents.
#      (b) Pass each page_content through an embedding model (e.g.
#          sentence-transformers, OpenAI ada-002) to obtain a vector.
#      (c) Store the (vector, metadata) pair in a vector database
#          (Chroma, FAISS, Qdrant, etc.).
#      (d) At query time, the retriever encodes the user query,
#          searches for nearest neighbours, and returns the matching
#          Document(s) for LLM-based answer generation.
# ══════════════════════════════════════════════════════════════════════
