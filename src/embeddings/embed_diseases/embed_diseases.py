"""
embed_diseases.py
──────────────────
Disease Embedding → ChromaDB Pipeline

Loads pre-chunked disease JSON records and generates dense embeddings
using BAAI/bge-m3 via sentence-transformers. Persists them in a
ChromaDB collection for retrieval.

Mirrors `src/embeddings/embed_drugs/embed_drugs.py` conventions so
disease retrieval is compatible with the existing project setup.

Usage (from project root):
    python src/embeddings/embed_diseases/embed_diseases.py
    python src/embeddings/embed_diseases/embed_diseases.py --mode overwrite

Optional custom paths:
    python src/embeddings/embed_diseases/embed_diseases.py ^
        --input-glob "data/Chunked_Data/diseases_chunked/*_chunked.json" ^
        --chroma data/vectorstores/diseases_chroma ^
        --collection diseases
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Optional

import chromadb
import torch
from sentence_transformers import SentenceTransformer

# ──────────────────────────────────────────────────────────────────────
# Defaults (overridable via CLI)
# ──────────────────────────────────────────────────────────────────────

DEFAULT_INPUT_GLOB = (
    "data/Chunked_Data/diseases_chunked/*.json"
)
DEFAULT_CHROMA_PATH = "data/vectorstores/diseases_chroma"
DEFAULT_COLLECTION_NAME = "diseases"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_DIMENSION = 384
DEFAULT_BATCH_SIZE = 16
DEFAULT_MODE = "skip_existing"  # "skip_existing" | "overwrite"


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
# Utilities: load & validate disease chunks
# ──────────────────────────────────────────────────────────────────────

def _iter_input_files(input_glob: str) -> list[Path]:
    root = Path.cwd()
    pattern = input_glob
    # Resolve the glob relative to CWD
    files = [Path(p) for p in root.glob(pattern) if Path(p).is_file()]
    files = sorted(files, key=lambda p: str(p))
    return files


def load_disease_chunk_files(input_glob: str) -> list[dict[str, Any]]:
    files = _iter_input_files(input_glob)
    if not files:
        raise FileNotFoundError(
            f"No disease chunk JSON files found for glob: {input_glob}"
        )

    all_chunks: list[dict[str, Any]] = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        if not isinstance(data, list):
            raise TypeError(
                f"Expected JSON array in {f}, got {type(data).__name__}"
            )

        logger.info("Loaded %d chunks from %s", len(data), f)
        all_chunks.extend(data)

    return all_chunks


def validate_disease_chunks(chunks: list[dict[str, Any]]) -> None:
    """
    Fail fast on structural issues before embedding (expensive).
    """
    required = [
        "chunk_id",
        "condition_id",
        "condition",
        "section",
        "chunk_type",
        "content",
        "text",
    ]

    errors: list[str] = []
    ids_seen: dict[str, int] = {}

    for idx, chunk in enumerate(chunks):
        label = f"Chunk {idx}"

        if not isinstance(chunk, dict):
            errors.append(f"{label}: not a dict (type={type(chunk).__name__})")
            continue

        cid = chunk.get("chunk_id")
        if not cid or not isinstance(cid, str):
            errors.append(f"{label}: missing/empty 'chunk_id'")
        else:
            if cid in ids_seen:
                errors.append(
                    f"Duplicate chunk_id '{cid}' (first seen at index {ids_seen[cid]})"
                )
            ids_seen[cid] = idx

        for field in required:
            if field not in chunk:
                errors.append(f"{label}: missing required field '{field}'")

        text = chunk.get("text")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{label}: 'text' is empty or not a string")

        for field in ["condition_id", "condition", "section", "chunk_type"]:
            v = chunk.get(field)
            if v is None or (isinstance(v, str) and not v.strip()):
                errors.append(f"{label}: '{field}' missing/empty")

    if errors:
        for e in errors[:30]:
            logger.error("  ❌ %s", e)
        if len(errors) > 30:
            logger.error("  … and %d more", len(errors) - 30)
        raise ValueError(
            f"Disease chunk validation failed with {len(errors)} error(s)."
        )

    logger.info("✅ Disease chunks validation passed: %d chunks", len(chunks))


# ──────────────────────────────────────────────────────────────────────
# Embedding model (BGE-M3)
# ──────────────────────────────────────────────────────────────────────

def detect_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_embedding_model(
    model_name: str,
    expected_dim: int,
    device: Optional[str] = None,
) -> tuple[SentenceTransformer, str]:
    if device is None:
        device = detect_device()

    logger.info("Loading embedding model: %s", model_name)
    logger.info("Device: %s", device)

    model = SentenceTransformer(model_name, device=device)
    dim = model.get_embedding_dimension()

    if dim != expected_dim:
        logger.warning(
            "⚠️ Model dimension is %d, expected %d. Proceeding but check compatibility.",
            dim,
            expected_dim,
        )
    else:
        logger.info("Model loaded — embedding dimension: %d", dim)

    return model, device


def embed_batch(
    model: SentenceTransformer,
    texts: list[str],
    batch_size: int,
) -> list[list[float]]:
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,  # L2-normalized vectors
        convert_to_numpy=True,
    )
    return embeddings.tolist()


# ──────────────────────────────────────────────────────────────────────
# ChromaDB setup
# ──────────────────────────────────────────────────────────────────────

def get_or_create_collection(
    chroma_path: str | Path,
    collection_name: str,
    embedding_model: str,
    embedding_dimension: int,
) -> tuple[chromadb.ClientAPI, chromadb.Collection]:
    path = Path(chroma_path)
    path.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(path))

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={
            "hnsw:space": "cosine",
            "embedding_model": embedding_model,
            "embedding_dimension": embedding_dimension,
            "normalized": True,
            "description": "Disease chunks embedded with BGE-M3 dense vectors",
        },
    )

    logger.info(
        "ChromaDB collection '%s' — %d existing documents",
        collection_name,
        collection.count(),
    )

    return client, collection


def sanitise_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """
    Chroma metadata rules:
      - omit None values
      - allow scalar values and list[str]
      - JSON-serialize unsupported nested objects
    """
    cleaned: dict[str, Any] = {}

    for key, value in meta.items():
        if value is None:
            continue

        if isinstance(value, list):
            if all(isinstance(v, str) for v in value):
                cleaned[key] = value
            else:
                cleaned[key] = json.dumps(value, ensure_ascii=False)
            continue

        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
            continue

        cleaned[key] = json.dumps(value, ensure_ascii=False)

    return cleaned


def build_chroma_record(chunk: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """
    Map disease chunk JSON → (id, document, metadata) for Chroma.
    """
    chunk_id: str = chunk["chunk_id"]
    text: str = chunk["text"]

    # Keep metadata lightweight for Chroma.
    meta: dict[str, Any] = {
        "condition_id": chunk.get("condition_id"),
        "condition": chunk.get("condition"),
        "section": chunk.get("section"),
        "subsection": chunk.get("subsection"),
        "chunk_type": chunk.get("chunk_type"),
        "source_url": chunk.get("source_url"),
    }

    # If source is present, store it as a JSON string for provenance.
    source = chunk.get("source")
    if source is not None:
        meta["source"] = source

    # Optional: store "content" for debugging/provenance, but avoid the
    # metadata blow-up. Store only if it's already a small dict;
    # otherwise it will be JSON-serialized anyway.
    content = chunk.get("content")
    if content is not None:
        meta["content"] = content

    return chunk_id, text, sanitise_metadata(meta)


def process_chunks(
    chunks: list[dict[str, Any]],
    model: SentenceTransformer,
    collection: chromadb.Collection,
    batch_size: int,
    mode: str,
) -> dict[str, int]:
    stats = {
        "total_input": len(chunks),
        "already_existing": 0,
        "embedded": 0,
        "skipped": 0,
        "failed": 0,
    }

    ids_all = [c["chunk_id"] for c in chunks]

    if mode == "skip_existing":
        existing_ids: set[str] = set()
        for i in range(0, len(ids_all), 5000):
            batch_ids = ids_all[i : i + 5000]
            result = collection.get(ids=batch_ids, include=[])
            existing_ids.update(result["ids"])

        stats["already_existing"] = len(existing_ids)
        logger.info("Skipping %d disease chunks already in Chroma", len(existing_ids))

        chunks_to_process = [c for c in chunks if c["chunk_id"] not in existing_ids]
    else:
        chunks_to_process = list(chunks)

    if not chunks_to_process:
        logger.info("No new disease chunks to embed.")
        return stats

    total = len(chunks_to_process)
    logger.info("Embedding %d disease chunks (batch_size=%d) …", total, batch_size)

    t_start = time.perf_counter()

    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = chunks_to_process[batch_start:batch_end]

        batch_ids: list[str] = []
        batch_texts: list[str] = []
        batch_metadatas: list[dict[str, Any]] = []
        batch_failures: int = 0

        for c in batch:
            try:
                cid, doc, meta = build_chroma_record(c)
                batch_ids.append(cid)
                batch_texts.append(doc)
                batch_metadatas.append(meta)
            except Exception as exc:
                stats["failed"] += 1
                batch_failures += 1
                logger.warning("Preparation failed: %s", exc)

        if not batch_texts:
            continue

        try:
            embeddings = embed_batch(model, batch_texts, batch_size=batch_size)

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
            stats["failed"] += len(batch_ids)
            logger.error("Batch %d–%d failed: %s", batch_start, batch_end, exc)

        processed = batch_end
        elapsed = time.perf_counter() - t_start
        if (batch_start // batch_size) % 10 == 9 or processed == total:
            rate = processed / elapsed if elapsed > 0 else 0
            logger.info("  Progress: %d / %d  (%.1f chunks/sec)", processed, total, rate)

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()

    stats["skipped"] = stats["already_existing"]
    return stats


def validate_collection(
    collection: chromadb.Collection,
    expected_new_or_total: int,
) -> None:
    """
    Post-write sanity checks.

    For overwrite mode, expected count == expected_new_or_total.
    For skip-existing mode, count may be >= expected_new_or_total
    because previously stored docs remain.
    """
    stored_count = collection.count()

    logger.info("─" * 56)
    logger.info("  Post-Embedding Validation")
    logger.info("─" * 56)
    logger.info("  Expected documents:  %d", expected_new_or_total)
    logger.info("  Stored in Chroma:    %d", stored_count)

    if stored_count >= expected_new_or_total:
        logger.info("  ✅ Count OK")
    else:
        logger.warning("  ⚠️ Count mismatch: expected %d, found %d", expected_new_or_total, stored_count)

    if stored_count > 0:
        sample = collection.peek(limit=1)
        embeddings = sample.get("embeddings")
        if embeddings is not None and len(embeddings) > 0:
            dim = len(embeddings[0])
            logger.info("  Sample embedding dimension: %d", dim)


def save_manifest(
    chroma_path: str | Path,
    stats: dict[str, int],
    embedding_model: str,
    embedding_dimension: int,
    collection_name: str,
) -> None:
    manifest = {
        "embedding_model": embedding_model,
        "embedding_dimension": embedding_dimension,
        "distance_metric": "cosine",
        "normalized": True,
        "collection_name": collection_name,
        "total_chunks_input": stats["total_input"],
        "newly_embedded": stats["embedded"],
        "skipped_existing": stats["skipped"],
        "failed": stats["failed"],
        "timestamp_unix": int(time.time()),
    }
    manifest_path = Path(chroma_path) / "embedding_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    logger.info("Manifest saved to %s", manifest_path)


def print_summary(
    stats: dict[str, int],
    chroma_path: str | Path,
    collection_name: str,
    device: str,
    elapsed: float,
    embedding_model: str,
    embedding_dimension: int,
) -> None:
    logger.info("═" * 56)
    logger.info("  Embedding Pipeline Summary (Diseases)")
    logger.info("═" * 56)
    logger.info("  Input chunks:        %d", stats["total_input"])
    logger.info("  Already existing:    %d", stats["already_existing"])
    logger.info("  Newly embedded:      %d", stats["embedded"])
    logger.info("  Skipped:             %d", stats["skipped"])
    logger.info("  Failed:              %d", stats["failed"])
    logger.info("")
    logger.info("  Embedding model:     %s", embedding_model)
    logger.info("  Embedding dimension: %d", embedding_dimension)
    logger.info("  Distance metric:     cosine")
    logger.info("  Normalized:          True")
    logger.info("  Device:              %s", device)
    logger.info("")
    logger.info("  Collection:          %s", collection_name)
    logger.info("  ChromaDB path:       %s", Path(chroma_path).resolve())
    logger.info("  Time elapsed:        %.1f seconds", elapsed)
    logger.info("═" * 56)


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main(
    input_glob: str,
    chroma_path: str,
    collection_name: str,
    embedding_model: str,
    embedding_dimension: int,
    batch_size: int,
    mode: str,
) -> None:
    t0 = time.perf_counter()

    chunks = load_disease_chunk_files(input_glob=input_glob)
    validate_disease_chunks(chunks)

    model, device = load_embedding_model(
        model_name=embedding_model,
        expected_dim=embedding_dimension,
        device=None,
    )

    _, collection = get_or_create_collection(
        chroma_path=chroma_path,
        collection_name=collection_name,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension,
    )

    stats = process_chunks(
        chunks=chunks,
        model=model,
        collection=collection,
        batch_size=batch_size,
        mode=mode,
    )

    # In skip_existing mode, stored_count may include already existing docs,
    # so we validate with lower bound.
    validate_collection(collection, expected_new_or_total=len(chunks))

    save_manifest(
        chroma_path=chroma_path,
        stats=stats,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension,
        collection_name=collection_name,
    )

    elapsed = time.perf_counter() - t0
    print_summary(
        stats=stats,
        chroma_path=chroma_path,
        collection_name=collection_name,
        device=device,
        elapsed=elapsed,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension,
    )

    # Helpful non-zero exit on obviously wrong results.
    if stats["failed"] > 0:
        logger.warning("Embedding finished with failures=%d", stats["failed"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Embed disease chunk JSON into ChromaDB using BGE-M3."
    )
    parser.add_argument(
        "--input-glob",
        default=DEFAULT_INPUT_GLOB,
        help="Glob for input chunk JSON files (default: %(default)s)",
    )
    parser.add_argument(
        "--chroma",
        default=DEFAULT_CHROMA_PATH,
        help="ChromaDB persistence directory (default: %(default)s)",
    )
    parser.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION_NAME,
        help="ChromaDB collection name (default: %(default)s)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Embedding batch size (default: %(default)s)",
    )
    parser.add_argument(
        "--mode",
        choices=["skip_existing", "overwrite"],
        default=DEFAULT_MODE,
        help="Processing mode (default: %(default)s)",
    )
    parser.add_argument(
        "--embedding-model",
        default=DEFAULT_EMBEDDING_MODEL,
        help="Sentence-transformers model name (default: %(default)s)",
    )
    parser.add_argument(
        "--embedding-dimension",
        type=int,
        default=DEFAULT_EMBEDDING_DIMENSION,
        help="Expected embedding dimension (default: %(default)s)",
    )

    args = parser.parse_args()
    main(
        input_glob=args.input_glob,
        chroma_path=args.chroma,
        collection_name=args.collection,
        embedding_model=args.embedding_model,
        embedding_dimension=args.embedding_dimension,
        batch_size=args.batch_size,
        mode=args.mode,
    )

