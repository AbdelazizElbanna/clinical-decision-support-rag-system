"""
query_rewrite_eval.py
---------------------
Measures how much the Intent Extractor's query rewriting IMPROVES retrieval.

For each question:
  1. Retrieve with ORIGINAL user query
  2. Extract intent to get the rewritten `search_query_en`
  3. Retrieve with REWRITTEN query
  4. Compare Hit Rate before vs after

Usage:
    python backend/query_rewrite_eval.py
"""
import json
import os
import sys
import glob

sys.path.append(r"e:\salah\salah_programing\clinical-decision-support-ref\backend")

from retriever import _get_disease_model, _get_collections
from intent_extractor import extract_intent

K_VALUE = 10
BASE_DIR = r"e:\salah\salah_programing\clinical-decision-support-ref\evaluation_questions"
OUTPUT_PATH = r"e:\salah\salah_programing\clinical-decision-support-ref\query_rewrite_results.json"

# Use Arabic questions to test the rewriter (they benefit most from translation)
ARABIC_SAMPLE = [
    {"question_text": "عندي حكة كتير في الجلد وجلدي بيجف، إيه المشكلة؟", "target_chunk_ids": ["eczema_core_symptom_01"]},
    {"question_text": "الصدفية بتأثر على الجلد إزاي؟", "target_chunk_ids": ["psoriasis_overview"]},
    {"question_text": "ما هي أعراض الشرى؟", "target_chunk_ids": ["urticaria_overview"]},
    {"question_text": "كيف أعالج الأكزيما في المنزل؟", "target_chunk_ids": ["eczema_core_management_01"]},
    {"question_text": "هل الإجهاد يزيد من حدة الصدفية؟", "target_chunk_ids": ["psoriasis_core_trigger_01"]},
]


def hit_at_k(retrieved_ids, target_ids, k):
    return any(rid in target_ids for rid in retrieved_ids[:k])


def main():
    print("--- Query Rewriting Evaluation ---\n")

    dis_col, _ = _get_collections()
    model = _get_disease_model()

    questions = ARABIC_SAMPLE

    # Also load some from files
    for filepath in glob.glob(os.path.join(BASE_DIR, "disease", "*.json")):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Only add questions that look like they'd benefit from rewriting (short or vague)
            for q in data:
                if q.get("question_text", "").strip() and len(q["question_text"]) < 80:
                    questions.append(q)
        if len(questions) >= 20:
            break

    questions = questions[:20]
    print(f"Evaluating {len(questions)} questions...\n")

    original_hits = 0
    rewritten_hits = 0
    results = []

    for i, q in enumerate(questions):
        q_text = q["question_text"]
        target_ids = q.get("target_chunk_ids", [])
        if not target_ids:
            continue

        # ── Retrieve with ORIGINAL query ──────────────────────────────────────
        orig_emb = model.encode(q_text).tolist()
        orig_res = dis_col.query(query_embeddings=[orig_emb], n_results=K_VALUE)
        orig_ids = orig_res["ids"][0] if orig_res.get("ids") else []
        orig_hit = hit_at_k(orig_ids, target_ids, K_VALUE)

        # ── Extract intent → get rewritten query ──────────────────────────────
        try:
            intent = extract_intent(q_text, {}, {})
            rewritten_q = intent.get("search_query_en", q_text)
        except Exception as e:
            print(f"  Intent extraction error: {e}")
            rewritten_q = q_text

        # ── Retrieve with REWRITTEN query ─────────────────────────────────────
        rw_emb = model.encode(rewritten_q).tolist()
        rw_res = dis_col.query(query_embeddings=[rw_emb], n_results=K_VALUE)
        rw_ids = rw_res["ids"][0] if rw_res.get("ids") else []
        rw_hit = hit_at_k(rw_ids, target_ids, K_VALUE)

        if orig_hit:
            original_hits += 1
        if rw_hit:
            rewritten_hits += 1

        improvement = "✅ Improved" if rw_hit and not orig_hit else (
                      "🔴 Degraded" if orig_hit and not rw_hit else
                      "➡️  Same")

        print(f"[{i+1}] {q_text[:50]}")
        print(f"      Rewritten: {rewritten_q[:60]}")
        print(f"      Original hit: {orig_hit} | Rewritten hit: {rw_hit} | {improvement}\n")

        results.append({
            "question": q_text,
            "rewritten_query": rewritten_q,
            "target_ids": target_ids,
            "original_hit": orig_hit,
            "rewritten_hit": rw_hit,
            "outcome": improvement,
        })

    total = len(results)
    orig_rate  = original_hits  / total * 100 if total > 0 else 0
    rw_rate    = rewritten_hits / total * 100 if total > 0 else 0
    delta      = rw_rate - orig_rate

    print("=" * 60)
    print("QUERY REWRITING EVALUATION RESULTS")
    print("=" * 60)
    print(f"  Total evaluated:              {total}")
    print(f"  Original query  Hit Rate@{K_VALUE}: {orig_rate:.1f}%")
    print(f"  Rewritten query Hit Rate@{K_VALUE}: {rw_rate:.1f}%")
    print(f"  Delta:                        {'+'if delta>=0 else ''}{delta:.1f}%")

    if delta > 5:
        print("\n  ✅ Rewriting SIGNIFICANTLY improves retrieval")
    elif delta > 0:
        print("\n  ✅ Rewriting modestly improves retrieval")
    elif delta == 0:
        print("\n  ➡️  Rewriting has neutral effect")
    else:
        print("\n  ⚠️  Rewriting slightly degrades retrieval (consider tuning the prompt)")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "original_hit_rate": round(orig_rate, 2),
            "rewritten_hit_rate": round(rw_rate, 2),
            "delta_pct": round(delta, 2),
            "details": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
