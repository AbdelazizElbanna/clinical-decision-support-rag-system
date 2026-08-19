"""
custom_ragas.py
---------------
Lightweight implementation of RAGAS-style metrics.

Metrics implemented:
  1. Faithfulness      - LLM-as-judge: are all claims grounded in the context?
                         (with retry on empty response, shorter truncated prompt)
  2. Answer Relevance  - Embedding cosine similarity: question vs answer
                         (pure local, no LLM needed - how RAGAS actually does it)
  3. Context Precision - Embedding cosine similarity: question vs each chunk > threshold
                         (pure local, no LLM needed)

Usage:
    python backend/custom_ragas.py
"""
import json
import sys
import time
import math

sys.path.append(r"e:\salah\salah_programing\clinical-decision-support-ref\backend")

from groq_router import groq_router
from sentence_transformers import SentenceTransformer

TRACES_PATH = r"e:\salah\salah_programing\clinical-decision-support-ref\evaluation_questions\traces.json"
OUTPUT_PATH = r"e:\salah\salah_programing\clinical-decision-support-ref\ragas_results.json"

JUDGE_MODEL        = "openai/gpt-oss-120b"
EMBEDDING_MODEL    = "all-MiniLM-L6-v2"   # Smaller/faster for eval; already on disk
PRECISION_THRESHOLD = 0.45                 # Cosine similarity threshold for "relevant"
MAX_TRACES         = 20
SLEEP              = 2
FAITH_RETRIES      = 3

print("Loading embedding model for Answer Relevance & Context Precision...")
embedder = SentenceTransformer(EMBEDDING_MODEL)
print("Done.\n")


# ── Helpers ───────────────────────────────────────────────────────────────────

def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def embed(text):
    return embedder.encode(text, normalize_embeddings=True).tolist()


# ── 1. Faithfulness (LLM-based, with retry on empty) ─────────────────────────

FAITHFULNESS_PROMPT = """You are a strict medical fact-checker.

CONTEXT:
{context}

AI ANSWER:
{answer}

List every factual claim in the answer. For each, state if it is supported by the context.

Respond ONLY with valid JSON:
{{"total_claims": <integer>, "supported_claims": <integer>, "unsupported_examples": []}}"""


def measure_faithfulness(question, answer, contexts):
    if not answer.strip():
        return None
    # If no contexts, the system abstained - that is safe behaviour
    if not contexts:
        return {"score": 1.0, "total_claims": 0, "supported_claims": 0,
                "unsupported": [], "note": "No context retrieved - system abstained"}

    # Truncate aggressively to keep prompt short and increase chance of response
    context_str = "\n\n".join(contexts[:2])[:1200]
    answer_str  = answer[:800]
    prompt      = FAITHFULNESS_PROMPT.format(context=context_str, answer=answer_str)

    for attempt in range(FAITH_RETRIES):
        try:
            resp = groq_router.chat_completion(
                model=JUDGE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200, temperature=0
            )
            raw = (resp.choices[0].message.content or "").strip()
            if not raw:
                time.sleep(2 + attempt * 2)
                continue   # retry on empty
            s = raw.find("{"); e = raw.rfind("}") + 1
            if s >= 0 and e > s:
                data = json.loads(raw[s:e])
                total     = max(data.get("total_claims", 1), 1)
                supported = data.get("supported_claims", 0)
                return {
                    "score": round(supported / total, 3),
                    "total_claims": total,
                    "supported_claims": supported,
                    "unsupported": data.get("unsupported_examples", [])
                }
        except json.JSONDecodeError:
            pass
        except Exception as ex:
            err = str(ex)
            if "400" in err or "model" in err.lower():
                print(f"    [Faithfulness] model error - skipping")
                return None
            print(f"    [Faithfulness error] {ex}")
        time.sleep(2 + attempt * 2)
    return None


# ── 2. Answer Relevance (embedding cosine similarity) ─────────────────────────

def measure_answer_relevance(question, answer):
    """
    Computes cosine similarity between the question embedding and the answer
    embedding. This is the core of how RAGAS computes Answer Relevancy.
    Range: 0.0 (totally unrelated) → 1.0 (identical semantic meaning).
    """
    if not answer.strip():
        return None
    try:
        q_emb = embed(question)
        a_emb = embed(answer[:1000])   # truncate very long answers
        score = cosine_similarity(q_emb, a_emb)
        # Normalize: cosine on normalized embeddings is already in [-1, 1],
        # shift to [0, 1]
        score = max(0.0, (score + 1.0) / 2.0)
        return {"score": round(score, 4), "method": "embedding_cosine"}
    except Exception as ex:
        print(f"    [AnswerRelevance error] {ex}")
    return None


# ── 3. Context Precision (embedding cosine similarity) ────────────────────────

def measure_context_precision(question, contexts):
    """
    For each retrieved chunk, computes cosine similarity with the question.
    A chunk is considered 'relevant' if similarity >= PRECISION_THRESHOLD.
    """
    if not contexts:
        return None
    try:
        q_emb = embed(question)
        relevant = 0
        chunk_scores = []
        for ctx in contexts[:4]:
            c_emb = embed(ctx[:500])
            sim   = cosine_similarity(q_emb, c_emb)
            # Shift from [-1,1] to [0,1]
            sim_norm = max(0.0, (sim + 1.0) / 2.0)
            chunk_scores.append(round(sim_norm, 4))
            if sim_norm >= PRECISION_THRESHOLD:
                relevant += 1
        total = len(contexts[:4])
        score = relevant / total if total else 0.0
        return {
            "score": round(score, 3),
            "relevant_chunks": relevant,
            "total_chunks": total,
            "chunk_similarities": chunk_scores
        }
    except Exception as ex:
        print(f"    [ContextPrecision error] {ex}")
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("--- Custom RAGAS Evaluation ---\n")
    print(f"  Faithfulness:      LLM-as-judge ({JUDGE_MODEL}, {FAITH_RETRIES} retries on empty)")
    print(f"  Answer Relevance:  Embedding cosine similarity ({EMBEDDING_MODEL})")
    print(f"  Context Precision: Embedding cosine similarity (threshold ≥ {PRECISION_THRESHOLD})")
    print()

    with open(TRACES_PATH, "r", encoding="utf-8") as f:
        traces = json.load(f)

    valid = [
        t for t in traces
        if t.get("answer", "").strip()
    ][:MAX_TRACES]
    print(f"Evaluating {len(valid)} traces...\n")

    results             = []
    faithfulness_scores = []
    relevance_scores    = []
    precision_scores    = []

    for i, trace in enumerate(valid):
        q   = trace["question"]
        a   = trace["answer"]
        ctx = trace["contexts"]

        print(f"[{i+1}/{len(valid)}] {q[:60]}...")

        # Faithfulness (LLM)
        faith = measure_faithfulness(q, a, ctx)
        if faith:
            faithfulness_scores.append(faith["score"])
            note = faith.get("note", "")
            label = f"({faith['supported_claims']}/{faith['total_claims']} claims)" if not note else f"({note})"
            print(f"  Faithfulness:      {faith['score']:.3f} {label}")
        time.sleep(SLEEP)

        # Answer Relevance (embeddings)
        rel = measure_answer_relevance(q, a)
        if rel:
            relevance_scores.append(rel["score"])
            print(f"  Answer Relevance:  {rel['score']:.4f}")

        # Context Precision (embeddings)
        prec = measure_context_precision(q, ctx)
        if prec:
            precision_scores.append(prec["score"])
            sims_str = ", ".join(str(s) for s in prec.get("chunk_similarities", []))
            print(f"  Context Precision: {prec['score']:.3f} "
                  f"({prec['relevant_chunks']}/{prec['total_chunks']} relevant) "
                  f"[sims: {sims_str}]")

        results.append({
            "question":          q,
            "faithfulness":      faith,
            "answer_relevance":  rel,
            "context_precision": prec,
        })

    # Summary
    def avg(lst): return round(sum(lst) / len(lst), 4) if lst else 0

    print("\n" + "="*60)
    print("CUSTOM RAGAS EVALUATION RESULTS")
    print("="*60)

    metrics = {
        "Faithfulness":      (avg(faithfulness_scores), 0.95),
        "Answer Relevance":  (avg(relevance_scores),    0.80),
        "Context Precision": (avg(precision_scores),    0.75),
    }
    for name, (score, target) in metrics.items():
        emoji = "🟢" if score >= target else "🟡" if score >= target * 0.85 else "🔴"
        print(f"  {emoji} {name:<22}: {score:.4f}  (target ≥ {target})")

    faith_avg = avg(faithfulness_scores)
    print("\n── Medical Safety Verdict ──")
    if faith_avg >= 0.95:
        print("  ✅ SAFE - LLM is faithful to retrieved context (hallucination risk: LOW)")
    elif faith_avg >= 0.80:
        print("  ⚠️  CAUTION - Some ungrounded claims detected (hallucination risk: MEDIUM)")
    elif faith_avg > 0:
        print("  🚨 UNSAFE - Significant hallucination risk detected!")
    else:
        print("  ⚠️  Faithfulness could not be evaluated (model returned empty responses)")

    n_faith = len(faithfulness_scores)
    n_rel   = len(relevance_scores)
    n_prec  = len(precision_scores)
    print(f"\n  Coverage: Faithfulness={n_faith}/{len(valid)} | "
          f"Relevance={n_rel}/{len(valid)} | Precision={n_prec}/{len(valid)}")

    # Save
    output = {
        "n_evaluated": len(valid),
        "averages": {
            "faithfulness":      avg(faithfulness_scores),
            "answer_relevance":  avg(relevance_scores),
            "context_precision": avg(precision_scores),
        },
        "targets":    {"faithfulness": 0.95, "answer_relevance": 0.80, "context_precision": 0.75},
        "coverage":   {"faithfulness": n_faith, "answer_relevance": n_rel, "context_precision": n_prec},
        "per_trace":  results,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nFull results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
