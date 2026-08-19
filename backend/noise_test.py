"""
noise_test.py
-------------
Tests whether the LLM gets misled by irrelevant (noisy) chunks.

For 20 questions:
  Round 1: Run pipeline normally (clean contexts)
  Round 2: Inject an irrelevant medical chunk into the contexts
  Compare: Did the LLM's answer change significantly?

If the LLM mentions the noisy chunk's content → it was misled.
If it ignores it → the system is Noise Robust.

Usage:
    python backend/noise_test.py
"""
import asyncio
import json
import sys
import time

sys.path.append(r"e:\salah\salah_programing\clinical-decision-support-ref\backend")
from pipeline import run_pipeline

# A known irrelevant chunk - about a completely different topic
NOISE_CHUNK = """
Drug Name: ASPIRIN 500MG 20 TABS
Active Ingredient: Acetylsalicylic Acid 500mg
Indications: Pain relief, fever reduction, anti-platelet
Contraindications: Peptic ulcer, bleeding disorders, Reye's syndrome in children
Dosage: 1-2 tablets every 4-6 hours as needed. MAX 4g/day
"""

TRACES_PATH = r"e:\salah\salah_programing\clinical-decision-support-ref\evaluation_questions\traces.json"
NOISE_RESULTS_OUTPUT = r"e:\salah\salah_programing\clinical-decision-support-ref\noise_test_results.json"
MAX_QUESTIONS = 20
SLEEP_BETWEEN = 3


def contains_noise_content(answer: str) -> bool:
    """Check if the LLM's answer references content from the noise chunk."""
    noise_keywords = [
        "aspirin", "acetylsalicylic", "500mg", "peptic ulcer",
        "reye", "anti-platelet", "4g/day", "acetylsalicylic acid"
    ]
    answer_lower = answer.lower()
    return any(kw in answer_lower for kw in noise_keywords)


async def run_with_noise_injection(question: str, clean_contexts: list) -> str:
    """
    Manually build a prompt with noisy context injected,
    then call the LLM directly.
    """
    from groq_router import groq_router
    from pipeline import SYSTEM_PROMPT
    from config import LLM_MODEL

    # Inject noise as the FIRST context (worst case scenario)
    noisy_contexts = [NOISE_CHUNK] + clean_contexts

    ctx_str = ""
    for i, ctx in enumerate(noisy_contexts, 1):
        ctx_str += f"\n[Source {i}]\n{ctx}\n"

    prompt = f"{ctx_str}\n\n[PATIENT QUERY]\n{question}\n\nBased ONLY on the context above, give a clinically helpful response. Respond ENTIRELY in English."

    response = groq_router.chat_completion(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1024,
        temperature=0.3
    )
    return response.choices[0].message.content or ""


async def run_noise_test():
    # Load pre-collected traces
    try:
        with open(TRACES_PATH, "r", encoding="utf-8") as f:
            traces = json.load(f)
    except FileNotFoundError:
        print("ERROR: traces.json not found. Run collect_traces.py first!")
        return

    valid_traces = [
        t for t in traces
        if t.get("answer", "").strip()
        and t.get("contexts")
    ][:MAX_QUESTIONS]

    print(f"Running Noise Robustness test on {len(valid_traces)} questions...\n")

    results = []
    noise_corrupted = 0

    for i, trace in enumerate(valid_traces):
        question = trace["question"]
        clean_answer = trace["answer"]
        clean_contexts = trace["contexts"]

        print(f"[{i+1}/{len(valid_traces)}] {question[:60]}...")

        try:
            noisy_answer = await run_with_noise_injection(question, clean_contexts)
            was_corrupted = contains_noise_content(noisy_answer)

            if was_corrupted:
                noise_corrupted += 1
                print(f"  🔴 CORRUPTED - LLM mentioned noise content!")
            else:
                print(f"  ✅ ROBUST - LLM ignored the noise")

            results.append({
                "question": question,
                "clean_answer": clean_answer,
                "noisy_answer": noisy_answer,
                "was_corrupted_by_noise": was_corrupted
            })

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            results.append({
                "question": question,
                "error": str(e)
            })

        if i < len(valid_traces) - 1:
            time.sleep(SLEEP_BETWEEN)

    # Summary
    total = len(valid_traces)
    robust = total - noise_corrupted
    robustness_rate = (robust / total * 100) if total else 0

    print("\n" + "="*60)
    print("NOISE ROBUSTNESS TEST RESULTS")
    print("="*60)
    print(f"  Total tested:    {total}")
    print(f"  Robust (ignored noise): {robust} ({robustness_rate:.1f}%)")
    print(f"  Corrupted (cited noise): {noise_corrupted} ({100-robustness_rate:.1f}%)")

    if robustness_rate >= 95:
        print("\n  ✅ EXCELLENT - System is highly resistant to irrelevant context")
    elif robustness_rate >= 80:
        print("\n  ⚠️  GOOD - Minor noise leakage, review System Prompt")
    else:
        print("\n  🚨 CRITICAL - System is easily misled by noisy context!")

    # Save
    output = {
        "robustness_rate_percent": robustness_rate,
        "total_tested": total,
        "robust_count": robust,
        "corrupted_count": noise_corrupted,
        "details": results
    }
    with open(NOISE_RESULTS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {NOISE_RESULTS_OUTPUT}")


if __name__ == "__main__":
    asyncio.run(run_noise_test())
