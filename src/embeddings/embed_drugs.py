"""
embed_drugs.py
──────────────
Drug Embedding → ChromaDB Pipeline using BAAI/bge-m3 dense embeddings.

Loads pre-chunked drug documents, generates dense embeddings with BGE-M3
via sentence-transformers, and persists them in a ChromaDB collection.

Strategy:
    1 drug document  →  1 dense embedding  →  1 Chroma record

Usage (from project root):
    conda run -n rag python src/embeddings/embed_drugs.py

    # Or with overwrite mode:
    conda run -n rag python src/embeddings/embed_drugs.py --mode overwrite

    # Custom paths:
    conda run -n rag python src/embeddings/embed_drugs.py \
        --input  data/docs/drugs_document/drugs_documents.json \
        --chroma data/vectorstores/drugs_chroma \
        --batch-size 16

Dependencies:
    pip install sentence-transformers chromadb torch
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import chromadb
import torch
from sentence_transformers import SentenceTransformer

# ══════════════════════════════════════════════════════════════════════
# Configuration defaults (overridable via CLI)
# ══════════════════════════════════════════════════════════════════════

INPUT_PATH = "data/docs/drugs_document/drugs_documents.json"
CHROMA_PATH = "data/vectorstores/drugs_chroma"
COLLECTION_NAME = "drugs"
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIMENSION = 1024
BATCH_SIZE = 16          # Conservative for ≤4 GB VRAM GPUs
MODE = "skip_existing"   # "skip_existing" or "overwrite"

# ══════════════════════════════════════════════════════════════════════
# Logging
# ══════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# 1. Load documents
# ══════════════════════════════════════════════════════════════════════

def load_documents(input_path: str | Path) -> list[dict[str, Any]]:
    """Load drug documents from the chunked JSON file."""
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise TypeError(
            f"Expected a JSON array at the top level, got: {type(data).__name__}"
        )

    logger.info("Loaded %d drug documents from %s", len(data), path)
    return data


# ══════════════════════════════════════════════════════════════════════
# 2. Validate documents (pre-embedding)
# ══════════════════════════════════════════════════════════════════════

def validate_documents(data: list[dict[str, Any]]) -> None:
    """
    Validate structural integrity before starting expensive embedding.

    Fails fast on:
        - Non-dict records
        - Missing id
        - Missing or empty page_content
        - Missing metadata dict
        - Duplicate IDs
    """
    errors: list[str] = []

    ids_seen: dict[str, int] = {}

    for idx, record in enumerate(data):
        label = f"Record {idx}"

        if not isinstance(record, dict):
            errors.append(f"{label}: not a dict (type={type(record).__name__})")
            continue

        # ID check
        doc_id = record.get("id")
        if not doc_id:
            errors.append(f"{label}: missing or empty 'id'")
        else:
            label = f"Record {idx} (id={doc_id})"
            if doc_id in ids_seen:
                errors.append(
                    f"{label}: duplicate ID (first seen at index {ids_seen[doc_id]})"
                )
            ids_seen[doc_id] = idx

        # page_content check
        pc = record.get("page_content")
        if pc is None:
            errors.append(f"{label}: missing 'page_content'")
        elif not isinstance(pc, str) or not pc.strip():
            errors.append(f"{label}: 'page_content' is empty or not a string")

        # metadata check
        meta = record.get("metadata")
        if meta is None:
            errors.append(f"{label}: missing 'metadata'")
        elif not isinstance(meta, dict):
            errors.append(f"{label}: 'metadata' is not a dict")

    if errors:
        for e in errors[:30]:
            logger.error("  ❌ %s", e)
        if len(errors) > 30:
            logger.error("  … and %d more errors", len(errors) - 30)
        raise ValueError(
            f"Input validation failed with {len(errors)} error(s). "
            "Fix the input data before embedding."
        )

    logger.info("✅ Input validation passed: %d documents, %d unique IDs",
                len(data), len(ids_seen))


# ══════════════════════════════════════════════════════════════════════
# 3. Load embedding model
# ══════════════════════════════════════════════════════════════════════

def detect_device() -> str:
    """Select the best available compute device."""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_embedding_model(
    model_name: str = EMBEDDING_MODEL,
    device: str | None = None,
) -> tuple[SentenceTransformer, str]:
    """
    Load BGE-M3 via sentence-transformers and move to the target device.

    Returns the model and the resolved device string.
    """
    if device is None:
        device = detect_device()

    logger.info("Loading embedding model: %s", model_name)
    logger.info("Device: %s", device)

    model = SentenceTransformer(model_name, device=device)

    # Verify output dimension
    dim = model.get_embedding_dimension()
    if dim != EMBEDDING_DIMENSION:
        logger.warning(
            "⚠️  Model dimension is %d, expected %d. "
            "Proceeding but check compatibility.", dim, EMBEDDING_DIMENSION
        )

    logger.info(
        "Model loaded — embedding dimension: %d, device: %s",
        dim, device,
    )

    return model, device


# ══════════════════════════════════════════════════════════════════════
# 4. Embed a batch of texts
# ══════════════════════════════════════════════════════════════════════

def embed_batch(
    model: SentenceTransformer,
    texts: list[str],
    batch_size: int = BATCH_SIZE,
) -> list[list[float]]:
    """
    Encode a batch of page_content texts into normalized dense vectors.

    Normalization:
        L2-normalised embeddings are used so that cosine distance in
        ChromaDB is equivalent to the inner product, which is the
        scoring method BGE-M3 is trained for.

    Returns a list of Python float lists (Chroma-compatible).
    """
    # sentence-transformers handles batching internally,
    # normalize_embeddings=True applies L2 normalization.
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,   # ← explicit L2 normalization
        convert_to_numpy=True,
    )

    # Convert numpy arrays → list[list[float]] for Chroma
    return embeddings.tolist()


# ══════════════════════════════════════════════════════════════════════
# 5. ChromaDB collection management
# ══════════════════════════════════════════════════════════════════════

def get_or_create_collection(
    chroma_path: str | Path,
    collection_name: str = COLLECTION_NAME,
) -> tuple[chromadb.ClientAPI, chromadb.Collection]:
    """
    Open (or create) a persistent ChromaDB collection configured for
    cosine similarity.

    Collection-level metadata records the embedding configuration for
    reproducibility.
    """
    path = Path(chroma_path)
    path.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(path))

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={
            "hnsw:space": "cosine",
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dimension": EMBEDDING_DIMENSION,
            "normalized": True,
            "description": "Drug documents embedded with BGE-M3 dense vectors",
        },
    )

    logger.info(
        "ChromaDB collection '%s' — %d existing documents",
        collection_name, collection.count(),
    )

    return client, collection


# ══════════════════════════════════════════════════════════════════════
# 6. Metadata sanitisation for Chroma
# ══════════════════════════════════════════════════════════════════════

def sanitise_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """
    Make metadata Chroma-compatible.

    ChromaDB (≥1.x) supports str, int, float, bool, and list[str]
    as metadata values, but does NOT support None.

    Rules applied:
        • None values → omitted entirely (Chroma would reject them)
        • list values → kept as-is if list[str]; otherwise JSON-serialised
        • All other types → kept unchanged
    """
    cleaned: dict[str, Any] = {}

    for key, value in meta.items():
        if value is None:
            # Omit — Chroma rejects None metadata values.
            # The absence of a key signals "not available" and is
            # distinguishable from an explicit value.
            continue
        elif isinstance(value, list):
            # Chroma supports list[str] natively in v1.x.
            # Ensure all elements are strings.
            if all(isinstance(v, str) for v in value):
                cleaned[key] = value
            else:
                cleaned[key] = json.dumps(value, ensure_ascii=False)
        else:
            cleaned[key] = value

    return cleaned


# ══════════════════════════════════════════════════════════════════════
# 7. Main processing loop
# ══════════════════════════════════════════════════════════════════════

def process_documents(
    data: list[dict[str, Any]],
    model: SentenceTransformer,
    collection: chromadb.Collection,
    batch_size: int = BATCH_SIZE,
    mode: str = MODE,
) -> dict[str, int]:
    """
    Embed and store all drug documents in ChromaDB.

    Supports two modes:
        "skip_existing"  — skip documents whose ID is already in Chroma
        "overwrite"      — upsert all documents regardless

    Returns a stats dict with counts.
    """
    stats = {
        "total_input": len(data),
        "already_existing": 0,
        "embedded": 0,
        "skipped": 0,
        "failed": 0,
    }

    # ── Determine which IDs need processing ────────────────────────
    all_ids = [doc["id"] for doc in data]

    if mode == "skip_existing":
        # Query Chroma for existing IDs in batches (get() has limits)
        existing_ids: set[str] = set()
        for i in range(0, len(all_ids), 5000):
            batch_ids = all_ids[i:i + 5000]
            result = collection.get(ids=batch_ids, include=[])
            existing_ids.update(result["ids"])

        stats["already_existing"] = len(existing_ids)

        if existing_ids:
            logger.info(
                "Skipping %d documents already in Chroma", len(existing_ids)
            )

        # Filter to only new documents
        docs_to_process = [
            doc for doc in data if doc["id"] not in existing_ids
        ]
    else:
        docs_to_process = list(data)

    if not docs_to_process:
        logger.info("No new documents to embed.")
        return stats

    logger.info(
        "Embedding %d documents (batch_size=%d) …",
        len(docs_to_process), batch_size,
    )

    # ── Process in batches ─────────────────────────────────────────
    total = len(docs_to_process)
    t_start = time.perf_counter()

    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = docs_to_process[batch_start:batch_end]

        batch_ids: list[str] = []
        batch_texts: list[str] = []
        batch_metadatas: list[dict[str, Any]] = []
        batch_failures: list[int] = []

        for i, doc in enumerate(batch):
            try:
                batch_ids.append(doc["id"])
                batch_texts.append(doc["page_content"])
                batch_metadatas.append(
                    sanitise_metadata(doc.get("metadata", {}))
                )
            except Exception as exc:
                idx = batch_start + i
                slug = doc.get("id", f"<unknown-{idx}>")
                logger.warning(
                    "Preparation failed for %s: %s", slug, exc
                )
                batch_failures.append(idx)
                stats["failed"] += 1

        if not batch_texts:
            continue

        try:
            # Generate embeddings with explicit L2 normalization
            embeddings = embed_batch(model, batch_texts, batch_size=batch_size)

            # Store in Chroma — use upsert for overwrite mode,
            # add for skip_existing (we already filtered).
            if mode == "overwrite":
                collection.upsert(
                    ids=batch_ids,
                    embeddings=embeddings,
                    documents=batch_texts,
                    metadatas=batch_metadatas,
                )
            else:
                collection.add(
                    ids=batch_ids,
                    embeddings=embeddings,
                    documents=batch_texts,
                    metadatas=batch_metadatas,
                )

            stats["embedded"] += len(batch_ids)

        except Exception as exc:
            logger.error(
                "Batch %d–%d failed: %s", batch_start, batch_end, exc
            )
            stats["failed"] += len(batch_ids)

        # Progress report every 10 batches
        processed = batch_end
        if (batch_start // batch_size) % 10 == 9 or processed == total:
            elapsed = time.perf_counter() - t_start
            rate = processed / elapsed if elapsed > 0 else 0
            logger.info(
                "  Progress: %d / %d  (%.1f docs/sec)",
                processed, total, rate,
            )

        # Release GPU memory between batches
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()

    stats["skipped"] = stats["already_existing"]

    return stats


# ══════════════════════════════════════════════════════════════════════
# 8. Post-embedding validation
# ══════════════════════════════════════════════════════════════════════

def validate_collection(
    collection: chromadb.Collection,
    expected_count: int,
) -> None:
    """
    Verify the ChromaDB collection after embedding.

    Checks:
        • Total document count matches expected
        • A sample embedding has the correct dimension
        • A sample record has metadata
    """
    stored_count = collection.count()

    logger.info("─" * 56)
    logger.info("  Post-Embedding Validation")
    logger.info("─" * 56)
    logger.info("  Expected documents:  %d", expected_count)
    logger.info("  Stored in Chroma:    %d", stored_count)

    if stored_count == expected_count:
        logger.info("  ✅ Count matches")
    elif stored_count >= expected_count:
        logger.info("  ✅ Count OK (includes previously stored docs)")
    else:
        logger.warning(
            "  ⚠️  Count mismatch: expected %d, found %d",
            expected_count, stored_count,
        )

    # Sample check — verify dimension and metadata on one record
    if stored_count > 0:
        sample = collection.peek(limit=1)

        embeddings = sample.get("embeddings")
        if embeddings is not None and len(embeddings) > 0:
            dim = len(embeddings[0])
            if dim == EMBEDDING_DIMENSION:
                logger.info("  ✅ Embedding dimension: %d", dim)
            else:
                logger.warning(
                    "  ⚠️  Embedding dimension: %d (expected %d)",
                    dim, EMBEDDING_DIMENSION,
                )

        metadatas = sample.get("metadatas")
        if metadatas is not None and len(metadatas) > 0:
            meta_keys = list(metadatas[0].keys())
            logger.info("  ✅ Sample metadata keys: %s", meta_keys)
        else:
            logger.warning("  ⚠️  No metadata found in sample")

    logger.info("─" * 56)


# ══════════════════════════════════════════════════════════════════════
# 9. Summary
# ══════════════════════════════════════════════════════════════════════

def print_summary(
    stats: dict[str, int],
    chroma_path: str | Path,
    collection_name: str,
    device: str,
    elapsed: float,
) -> None:
    """Print a final summary of the embedding run."""
    logger.info("═" * 56)
    logger.info("  Embedding Pipeline Summary")
    logger.info("═" * 56)
    logger.info("  Input documents:     %d", stats["total_input"])
    logger.info("  Already existing:    %d", stats["already_existing"])
    logger.info("  Newly embedded:      %d", stats["embedded"])
    logger.info("  Skipped:             %d", stats["skipped"])
    logger.info("  Failed:              %d", stats["failed"])
    logger.info("")
    logger.info("  Embedding model:     %s", EMBEDDING_MODEL)
    logger.info("  Embedding dimension: %d", EMBEDDING_DIMENSION)
    logger.info("  Distance metric:     cosine")
    logger.info("  Normalized:          True")
    logger.info("  Device:              %s", device)
    logger.info("")
    logger.info("  Collection:          %s", collection_name)
    logger.info("  ChromaDB path:       %s", Path(chroma_path).resolve())
    logger.info("  Time elapsed:        %.1f seconds", elapsed)
    logger.info("═" * 56)


# ══════════════════════════════════════════════════════════════════════
# 10. Manifest (reproducibility)
# ══════════════════════════════════════════════════════════════════════

def save_manifest(chroma_path: str | Path, stats: dict[str, int]) -> None:
    """
    Write a small JSON manifest alongside the Chroma DB for
    reproducibility and downstream pipeline configuration.
    """
    manifest = {
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "distance_metric": "cosine",
        "normalized": True,
        "collection_name": COLLECTION_NAME,
        "total_documents": stats["total_input"],
        "embedded": stats["embedded"],
        "skipped_existing": stats["skipped"],
        "failed": stats["failed"],
    }

    manifest_path = Path(chroma_path) / "embedding_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info("Manifest saved to %s", manifest_path)


# ══════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════

def main(
    input_path: str = INPUT_PATH,
    chroma_path: str = CHROMA_PATH,
    batch_size: int = BATCH_SIZE,
    mode: str = MODE,
) -> None:
    t0 = time.perf_counter()

    # ── 1. Load ────────────────────────────────────────────────────
    data = load_documents(input_path)

    # ── 2. Validate input ─────────────────────────────────────────
    validate_documents(data)

    # ── 3. Load model ─────────────────────────────────────────────
    model, device = load_embedding_model()

    # ── 4. Open / create Chroma collection ────────────────────────
    client, collection = get_or_create_collection(chroma_path)

    # ── 5. Embed and store ────────────────────────────────────────
    stats = process_documents(
        data=data,
        model=model,
        collection=collection,
        batch_size=batch_size,
        mode=mode,
    )

    # ── 6. Validate collection ────────────────────────────────────
    validate_collection(collection, expected_count=len(data))

    # ── 7. Save manifest ──────────────────────────────────────────
    save_manifest(chroma_path, stats)

    # ── 8. Summary ────────────────────────────────────────────────
    elapsed = time.perf_counter() - t0
    print_summary(stats, chroma_path, COLLECTION_NAME, device, elapsed)


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Embed drug documents with BGE-M3 and store in ChromaDB."
    )
    parser.add_argument(
        "--input", "-i",
        default=INPUT_PATH,
        help=f"Path to the drug documents JSON (default: {INPUT_PATH})",
    )
    parser.add_argument(
        "--chroma", "-c",
        default=CHROMA_PATH,
        help=f"ChromaDB persistence directory (default: {CHROMA_PATH})",
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=BATCH_SIZE,
        help=f"Embedding batch size (default: {BATCH_SIZE})",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["skip_existing", "overwrite"],
        default=MODE,
        help=f"Processing mode (default: {MODE})",
    )
    args = parser.parse_args()

    main(
        input_path=args.input,
        chroma_path=args.chroma,
        batch_size=args.batch_size,
        mode=args.mode,
    )
