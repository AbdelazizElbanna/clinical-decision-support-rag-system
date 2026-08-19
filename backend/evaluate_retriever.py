import json
import os
import sys
import glob
import math

sys.path.append(r"e:\salah\salah_programing\clinical-decision-support-ref\backend")

from retriever import _get_disease_model, _get_drug_model, _get_collections

K_VALUE = 10
REPORT_PATH = r"e:\salah\salah_programing\clinical-decision-support-ref\retrieval_evaluation_results.md"


def load_questions(pattern):
    questions = []
    for filepath in glob.glob(pattern):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            questions.extend(data)
    return questions


def calculate_ndcg(retrieved_ids, target_ids, k):
    """Normalized Discounted Cumulative Gain @k."""
    dcg = 0.0
    for i, rid in enumerate(retrieved_ids[:k]):
        if rid in target_ids:
            dcg += 1.0 / math.log2(i + 2)  # log2(rank+1), rank is 1-indexed so i+2

    # Ideal DCG: all relevant docs at top positions
    ideal_hits = min(len(target_ids), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))

    return dcg / idcg if idcg > 0 else 0.0


def calculate_precision_at_k(retrieved_ids, target_ids, k):
    """Precision@k = relevant retrieved / k"""
    retrieved_k = retrieved_ids[:k]
    relevant_retrieved = sum(1 for rid in retrieved_k if rid in target_ids)
    return relevant_retrieved / k if k > 0 else 0.0


def evaluate_questions(questions, collection_flag, domain_name):
    total = 0
    hits = 0
    mrr_sum = 0.0
    precision_sum = 0.0
    ndcg_sum = 0.0
    misses = []

    dis_col, drug_col = _get_collections()
    col = dis_col if collection_flag == "diseases" else drug_col
    model = _get_disease_model() if collection_flag == "diseases" else _get_drug_model()

    for q in questions:
        target_ids = q.get("target_chunk_ids", [])
        if not target_ids:
            continue

        total += 1
        query_text = q["question_text"]

        try:
            query_emb = model.encode(query_text).tolist()
            res = col.query(
                query_embeddings=[query_emb],
                n_results=K_VALUE,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            print(f"Error: {e}")
            continue

        retrieved_ids = res["ids"][0] if res.get("ids") else []

        # ── Hit Rate & MRR ────────────────────────────────────────────────────
        hit = False
        rank = 0
        for i, rid in enumerate(retrieved_ids):
            if rid in target_ids:
                hit = True
                rank = i + 1
                break

        if hit:
            hits += 1
            mrr_sum += 1.0 / rank
        else:
            misses.append({
                "id": q.get("question_id", "?"),
                "question": query_text,
                "expected": target_ids,
                "top3_retrieved": retrieved_ids[:3],
            })

        # ── Precision@k ───────────────────────────────────────────────────────
        precision_sum += calculate_precision_at_k(retrieved_ids, target_ids, K_VALUE)

        # ── NDCG@k ────────────────────────────────────────────────────────────
        ndcg_sum += calculate_ndcg(retrieved_ids, target_ids, K_VALUE)

    hit_rate = (hits / total) * 100 if total > 0 else 0
    mrr = mrr_sum / total if total > 0 else 0
    precision = precision_sum / total if total > 0 else 0
    ndcg = ndcg_sum / total if total > 0 else 0

    return {
        "domain": domain_name,
        "total": total,
        "hit_rate": hit_rate,
        "mrr": mrr,
        "precision_at_k": precision,
        "ndcg_at_k": ndcg,
        "misses": misses,
    }


def main():
    print(f"--- RAG Retriever Evaluation (K={K_VALUE}) ---\n")

    base_dir = r"e:\salah\salah_programing\clinical-decision-support-ref\evaluation_questions"

    print("Loading Disease questions...")
    disease_qs = load_questions(os.path.join(base_dir, "disease", "*.json"))
    print(f"Loaded {len(disease_qs)} disease questions with Ground Truth.\n")

    print("Loading Drug questions...")
    drug_qs = load_questions(os.path.join(base_dir, "drug", "*.json"))
    print(f"Loaded {len(drug_qs)} drug questions with Ground Truth.\n")

    print("Evaluating Disease Retriever...")
    dis_res = evaluate_questions(disease_qs, "diseases", "Disease")
    print(f"Disease - Total Evaluated: {dis_res['total']}")
    print(f"Disease - Hit Rate@{K_VALUE}:    {dis_res['hit_rate']:.2f}%")
    print(f"Disease - Precision@{K_VALUE}:   {dis_res['precision_at_k']:.4f}")
    print(f"Disease - MRR@{K_VALUE}:         {dis_res['mrr']:.4f}")
    print(f"Disease - NDCG@{K_VALUE}:        {dis_res['ndcg_at_k']:.4f}")

    print("\nEvaluating Drug Retriever...")
    drug_res = evaluate_questions(drug_qs, "drugs", "Drug")
    print(f"Drug - Total Evaluated: {drug_res['total']}")
    print(f"Drug - Hit Rate@{K_VALUE}:    {drug_res['hit_rate']:.2f}%")
    print(f"Drug - Precision@{K_VALUE}:   {drug_res['precision_at_k']:.4f}")
    print(f"Drug - MRR@{K_VALUE}:         {drug_res['mrr']:.4f}")
    print(f"Drug - NDCG@{K_VALUE}:        {drug_res['ndcg_at_k']:.4f}")

    # ── Save markdown report ──────────────────────────────────────────────────
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(f"# RAG Retrieval Evaluation Report (K={K_VALUE})\n\n")
        f.write("| Domain | Questions | Hit Rate@K | Precision@K | MRR@K | NDCG@K |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: |\n")
        for res in [dis_res, drug_res]:
            f.write(
                f"| **{res['domain']}** | {res['total']} "
                f"| {res['hit_rate']:.2f}% "
                f"| {res['precision_at_k']:.4f} "
                f"| {res['mrr']:.4f} "
                f"| {res['ndcg_at_k']:.4f} |\n"
            )
        f.write("\n")

        for res in [dis_res, drug_res]:
            if res["misses"]:
                f.write(f"## {res['domain']} — Missed Questions (Sample)\n")
                for m in res["misses"][:5]:
                    f.write(f"- **Q ({m['id']}):** {m['question']}\n")
                    f.write(f"  - *Expected:* `{m['expected']}`\n")
                    f.write(f"  - *Top-3 Retrieved:* `{m['top3_retrieved']}`\n\n")

    print(f"\nDetailed report saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
