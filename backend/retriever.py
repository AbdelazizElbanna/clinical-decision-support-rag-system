"""
ChromaDB retriever with dual-model lazy encoding.

Diseases collection: all-MiniLM-L6-v2 (384 dims)
Drugs collection:    BAAI/bge-m3        (1024 dims)

Encoding is lazy - only runs for the models actually needed by the query.
"""

from sentence_transformers import SentenceTransformer
from config import (
    CHROMA_DISEASES_DIR, CHROMA_DRUGS_DIR,
    DISEASES_COLLECTION, DRUGS_COLLECTION
)

# Separate model configs per collection
DISEASES_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DRUGS_EMBEDDING_MODEL    = "BAAI/bge-m3"

_model_diseases = None
_model_drugs    = None
_diseases_col   = None
_drugs_col      = None


def _get_disease_model():
    global _model_diseases
    if _model_diseases is None:
        print("Loading disease embedding model (all-MiniLM-L6-v2)...")
        _model_diseases = SentenceTransformer(DISEASES_EMBEDDING_MODEL)
    return _model_diseases


def _get_drug_model():
    global _model_drugs
    if _model_drugs is None:
        print("Loading drug embedding model (BAAI/bge-m3)...")
        _model_drugs = SentenceTransformer(DRUGS_EMBEDDING_MODEL)
    return _model_drugs


def _get_collections():
    global _diseases_col, _drugs_col
    import chromadb

    if _diseases_col is None:
        try:
            client_dis = chromadb.PersistentClient(path=CHROMA_DISEASES_DIR)
            _diseases_col = client_dis.get_collection(DISEASES_COLLECTION)
            print(f"Diseases ChromaDB ready: {_diseases_col.count()} disease chunks")
        except Exception as e:
            print(f"Diseases ChromaDB not ready ({e})")

    if _drugs_col is None:
        try:
            client_drugs = chromadb.PersistentClient(path=CHROMA_DRUGS_DIR)
            _drugs_col = client_drugs.get_collection(DRUGS_COLLECTION)
            print(f"Drugs ChromaDB ready: {_drugs_col.count()} drug chunks")
        except Exception as e:
            print(f"Drugs ChromaDB not ready ({e})")

    return _diseases_col, _drugs_col


def retrieve(
    query: str,
    collections_to_query: list,
    condition: str = None,
    n_per_collection: int = 3
) -> list:
    """
    Retrieve chunks using the correct model per collection.
    Encoding is lazy - only done when that collection is actually needed.
    """
    diseases_col, drugs_col = _get_collections()

    results = []

    # ── Diseases ──────────────────────────────────────────────────────────
    if "diseases" in collections_to_query and diseases_col is not None:
        # Lazy encode with the diseases model (384 dims)
        disease_model = _get_disease_model()
        disease_embedding = disease_model.encode(
            query, normalize_embeddings=True
        ).tolist()

        filter_meta = None
        if condition and condition not in ("Unknown", "General"):
            cid = condition.lower().replace(" ", "_")
            cid_map = {
                "eczema": "eczema_atopic_dermatitis",
                "psoriasis": "psoriasis",
                "urticaria": "urticaria_hives"
            }
            cid = cid_map.get(cid, cid)
            filter_meta = {"condition_id": cid}

        res = diseases_col.query(
            query_embeddings=[disease_embedding],
            n_results=n_per_collection,
            where=filter_meta
        )
        if res["documents"] and res["documents"][0]:
            for i, doc in enumerate(res["documents"][0]):
                results.append({
                    "text": doc,
                    "metadata": res["metadatas"][0][i],
                    "score": round(1 - res["distances"][0][i], 3),
                    "source": "diseases"
                })

    # ── Drugs ─────────────────────────────────────────────────────────────
    if "drugs" in collections_to_query and drugs_col is not None:
        # Lazy encode with the drugs model (1024 dims)
        drug_model = _get_drug_model()
        drug_embedding = drug_model.encode(
            f"query: {query}", normalize_embeddings=True
        ).tolist()

        res = drugs_col.query(
            query_embeddings=[drug_embedding],
            n_results=n_per_collection
        )
        if res["documents"] and res["documents"][0]:
            for i, doc in enumerate(res["documents"][0]):
                results.append({
                    "text": doc,
                    "metadata": res["metadatas"][0][i],
                    "score": round(1 - res["distances"][0][i], 3),
                    "source": "drugs"
                })

    return results
