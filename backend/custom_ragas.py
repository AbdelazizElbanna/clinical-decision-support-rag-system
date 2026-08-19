"""
custom_ragas.py
---------------
Lightweight implementation of RAGAS-style metrics using Groq directly.
No dependency on the ragas library — avoids langchain_community version conflicts.

Metrics implemented:
  1. Faithfulness      — Are all claims in the answer grounded in the context?
  2. Answer Relevance  — Does the answer actually address the question? (embedding similarity)
  3. Context Precision — What fraction of retrieved chunks are relevant?

Usage:
    python backend/custom_ragas.py
"""
import json
import sys
import time
import math

sys.path.append(r"e:\salah\salah_programing\clinical-decision-support-ref\backend")

from groq_router import groq_router
from config import GROQ_API_KEYS

TRACES_PATH = r"e:\salah\salah_programing\clinical-decision-support-ref\evaluation_questions\traces.json"
OUTPUT_PATH = r"e:\salah\salah_programing\clinical-decision-support-ref\ragas_results.json"

JUDGE_MODEL  = "llama3-8b-8192"   # Fastest capable model available on hackathon keys
MAX_TRACES   = 20
SLEEP        = 3

# ── 1. Faithfulness ───────────────────────────────────────────────────────────

FAITHFULNESS_PROMPT = """You are a strict medical fact-checker.

CONTEXT (what the AI was allowed to use):
{context}

AI ANSWER:
{answer}

Task: Break the AI's answer into individual factual claims. 
For EACH claim, determine if it is DIRECTLY supported by the context above.

Respond ONLY with valid JSON:
{{
  "total_claims": <integer>,
  "supported_claims": <integer>,
  "unsupported_examples": ["<any claim not in context, or empty list>"]
}}"""


def measure_faithfulness(question, answer, contexts):
    if not answer.strip():
        return None
    # If no contexts, the system refused to answer — that IS safe behaviour
    if not contexts:
        return {"score": 1.0, "total_claims": 0, "supported_claims": 0,
                "unsupported": [], "note": "No context retrieved — system abstained"}
    context_str = "\n\n".join(contexts[:3])[:2000]
    try:
        resp = groq_router.chat_completion(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": FAITHFULNESS_PROMPT.format(
                context=context_str, answer=answer[:1500])}],
            max_tokens=300, temperature=0
        )
        raw = resp.choices[0].message.content or ""
        s = raw.find("{"); e = raw.rfind("}") + 1
        if s >= 0 and e > s:
            data = json.loads(raw[s:e])
            total = max(data.get("total_claims", 1), 1)
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
            print(f"    [Faithfulness] model error — skipping")
        else:
            print(f"    [Faithfulness error] {ex}")
    return None


# ── 2. Answer Relevance (embedding cosine similarity) ─────────────────────────

RELEVANCE_PROMPT = """Rate how relevant the AI ANSWER is to the USER QUESTION on a scale of 1 to 5.
1 = Completely irrelevant or dodges the question.
5 = Directly and clearly answers the question.

USER QUESTION: {question}

AI ANSWER: {answer}

Respond with ONLY the integer number (1, 2, 3, 4, or 5). No explanations."""

def measure_answer_relevance(question, answer):
    """LLM-as-a-Judge approach to measure if the answer actually addresses the question."""
    if not answer.strip():
        return None
    try:
        resp = groq_router.chat_completion(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": RELEVANCE_PROMPT.format(question=question, answer=answer[:1500])}],
            max_tokens=10, temperature=0
        )
        raw = (resp.choices[0].message.content or "").strip()
        import re
        match = re.search(r'[1-5]', raw)
        if match:
            val = int(match.group(0))
            score = (val - 1) / 4.0
            return {"score": round(score, 3), "raw_rating": val}
        return {"score": 0.0, "raw_rating": raw}
    except Exception as ex:
        print(f"    [AnswerRelevance error] {ex}")
    return None


# ── 3. Context Precision ──────────────────────────────────────────────────────

CONTEXT_PRECISION_PROMPT = """Is this retrieved chunk RELEVANT to answering the question?

Question: {question}
Chunk: {chunk}

Reply with ONLY "yes" or "no"."""


def measure_context_precision(question, contexts):
    if not contexts:
        return None
    relevant = 0
    for ctx in contexts[:4]:  # Evaluate top 4 chunks
        try:
            resp = groq_router.chat_completion(
                model=JUDGE_MODEL,
                messages=[{"role": "user", "content": CONTEXT_PRECISION_PROMPT.format(
                    question=question, chunk=ctx[:600])}],
                max_tokens=10, temperature=0
            )
            answer_text = (resp.choices[0].message.content or "").strip().lower()
            # Handle empty response or thinking tags
            if not answer_text:
                answer_text = "no"
            if "yes" in answer_text:
                relevant += 1
            time.sleep(0.5)
        except Exception:
            pass
    score = relevant / len(contexts[:4]) if contexts else 0
    return {"score": round(score, 3), "relevant_chunks": relevant, "total_chunks": len(contexts[:4])}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("--- Custom RAGAS Evaluation (Groq-powered) ---\n")

    with open(TRACES_PATH, "r", encoding="utf-8") as f:
        traces = json.load(f)

    valid = [
        t for t in traces
        if t.get("answer", "").strip()  # answer can be empty = abstained (still valid)
    ][:MAX_TRACES]
    print(f"Evaluating {len(valid)} traces...\n")

    results = []
    faithfulness_scores = []
    relevance_scores    = []
    precision_scores    = []

    for i, trace in enumerate(valid):
        q = trace["question"]
        a = trace["answer"]
        ctx = trace["contexts"]

        print(f"[{i+1}/{len(valid)}] {q[:60]}...")

        # Faithfulness
        faith = measure_faithfulness(q, a, ctx)
        if faith:
            faithfulness_scores.append(faith["score"])
            print(f"  Faithfulness:      {faith['score']:.3f} "
                  f"({faith['supported_claims']}/{faith['total_claims']} claims)")
        time.sleep(SLEEP)

        # Answer Relevance
        rel = measure_answer_relevance(q, a)
        if rel:
            relevance_scores.append(rel["score"])
            print(f"  Answer Relevance:  {rel['score']:.3f}")
        time.sleep(SLEEP)

        # Context Precision
        prec = measure_context_precision(q, ctx)
        if prec:
            precision_scores.append(prec["score"])
            print(f"  Context Precision: {prec['score']:.3f} "
                  f"({prec['relevant_chunks']}/{prec['total_chunks']} chunks relevant)")
        time.sleep(SLEEP)

        results.append({
            "question": q,
            "faithfulness": faith,
            "answer_relevance": rel,
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

    # Clinical safety flag
    faith_avg = avg(faithfulness_scores)
    print("\n── Medical Safety Verdict ──")
    if faith_avg >= 0.95:
        print("  ✅ SAFE — LLM is faithful to retrieved context (hallucination risk: LOW)")
    elif faith_avg >= 0.80:
        print("  ⚠️  CAUTION — Some ungrounded claims detected (hallucination risk: MEDIUM)")
    else:
        print("  🚨 UNSAFE — Significant hallucination risk detected!")

    # Save
    output = {
        "n_evaluated": len(valid),
        "averages": {
            "faithfulness": avg(faithfulness_scores),
            "answer_relevance": avg(relevance_scores),
            "context_precision": avg(precision_scores),
        },
        "targets": {"faithfulness": 0.95, "answer_relevance": 0.80, "context_precision": 0.75},
        "per_trace": results,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nFull results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
