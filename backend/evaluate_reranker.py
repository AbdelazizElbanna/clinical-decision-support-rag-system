"""
evaluate_reranker.py
--------------------
Isolates and measures the Reranker's contribution.

For each evaluation question:
  1. Retrieves Top-K from vector DB (BEFORE reranking)
  2. Applies the cross-encoder reranker (AFTER reranking)
  3. Compares Precision@4 before vs after

This answers: "Is the Reranker actually helping?"

Usage:
    python backend/evaluate_reranker.py
"""
import json
import os
import sys
import glob
import math

sys.path.append(r"e:\salah\salah_programing\clinical-decision-support-ref\backend")

from retriever import _get_disease_model, _get_drug_model, _get_collections, retrieve

K_RETRIEVE = 10
K_RERANK = 4
BASE_DIR = r"e:\salah\salah_programing\clinical-decision-support-ref\evaluation_questions"


def load_questions(pattern):
    questions = []
    for filepath in glob.glob(pattern):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            questions.extend(data)
    return questions


def precision_at_k(retrieved_ids, target_ids, k):
    relevant = sum(1 for r in retrieved_ids[:k] if r in target_ids)
    return relevant / k if k > 0 else 0.0


def evaluate_reranker_for_domain(questions, collection_name, domain_name):
    dis_col, drug_col = _get_collections()
    col = dis_col if collection_name == "diseases" else drug_col
    model = _get_disease_model() if collection_name == "diseases" else _get_drug_model()

    # Try to load cross-encoder for reranking
    try:
        from sentence_transformers import CrossEncoder
        reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
        has_reranker = True
        print(f"  Cross-encoder loaded.")
    except Exception as e:
        print(f"  WARNING: Could not load cross-encoder: {e}")
        has_reranker = False

    total = 0
    pre_precision_sum = 0.0
    post_precision_sum = 0.0
    improvements = []

    for q in questions:
        target_ids = q.get("target_chunk_ids", [])
        if not target_ids:
            continue

        query_text = q["question_text"]
        if not query_text.strip():
            continue
        total += 1

        try:
            # ── Stage 1: Vector DB retrieval (BEFORE reranker) ────────────────
            query_emb = model.encode(query_text).tolist()
            res = col.query(
                query_embeddings=[query_emb],
                n_results=K_RETRIEVE,
                include=["documents", "metadatas", "distances"],
            )
            retrieved_ids   = res["ids"][0] if res.get("ids") else []
            retrieved_docs  = res["documents"][0] if res.get("documents") else []

            pre_p4 = precision_at_k(retrieved_ids, target_ids, K_RERANK)
            pre_precision_sum += pre_p4

            # ── Stage 2: Cross-Encoder Reranking (AFTER reranker) ─────────────
            if has_reranker and retrieved_docs:
                pairs = [(query_text, doc) for doc in retrieved_docs]
                scores = reranker.predict(pairs)
                ranked = sorted(
                    zip(retrieved_ids, scores),
                    key=lambda x: x[1], reverse=True
                )
                reranked_ids = [r[0] for r in ranked]
                post_p4 = precision_at_k(reranked_ids, target_ids, K_RERANK)
            else:
                # No reranker — assume same order
                reranked_ids = retrieved_ids
                post_p4 = pre_p4

            post_precision_sum += post_p4

            delta = post_p4 - pre_p4
            if delta != 0:
                improvements.append({
                    "question": query_text[:60],
                    "pre_p4": round(pre_p4, 3),
                    "post_p4": round(post_p4, 3),
                    "delta": round(delta, 3),
                })

        except Exception as e:
            print(f"  Error on '{query_text[:40]}': {e}")
            total -= 1

    pre_avg  = pre_precision_sum / total if total > 0 else 0
    post_avg = post_precision_sum / total if total > 0 else 0
    improvement = ((post_avg - pre_avg) / pre_avg * 100) if pre_avg > 0 else 0

    return {
        "domain": domain_name,
        "total": total,
        "pre_rerank_precision_at_4": pre_avg,
        "post_rerank_precision_at_4": post_avg,
        "relative_improvement_pct": improvement,
        "changed_questions": improvements[:5],  # Sample
    }


def main():
    print("--- Reranker Isolation Evaluation ---\n")

    disease_qs = load_questions(os.path.join(BASE_DIR, "disease", "*.json"))
    drug_qs    = load_questions(os.path.join(BASE_DIR, "drug",    "*.json"))

    print(f"Evaluating Disease Reranker ({len(disease_qs)} questions)...")
    dis_res = evaluate_reranker_for_domain(disease_qs, "diseases", "Disease")

    print(f"\nEvaluating Drug Reranker ({len(drug_qs)} questions)...")
    drug_res = evaluate_reranker_for_domain(drug_qs, "drugs", "Drug")

    print("\n" + "="*60)
    print("RERANKER EVALUATION RESULTS")
    print("="*60)
    for res in [dis_res, drug_res]:
        arrow = "🟢 +" if res["relative_improvement_pct"] > 0 else "🔴 "
        print(f"\n  {res['domain']} ({res['total']} questions):")
        print(f"    Before Reranking  Precision@4: {res['pre_rerank_precision_at_4']:.4f}")
        print(f"    After  Reranking  Precision@4: {res['post_rerank_precision_at_4']:.4f}")
        print(f"    Change: {arrow}{res['relative_improvement_pct']:+.1f}%")

    # Save results
    output_path = r"e:\salah\salah_programing\clinical-decision-support-ref\reranker_evaluation_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"disease": dis_res, "drug": drug_res}, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
