"""
latency_benchmark.py
--------------------
Measures end-to-end latency for the full RAG pipeline.
Reports: p50, p95, p99 latency (seconds), and per-stage breakdown.

Usage:
    python backend/latency_benchmark.py
"""
import asyncio
import json
import sys
import time
import glob
import statistics

sys.path.append(r"e:\salah\salah_programing\clinical-decision-support-ref\backend")

from pipeline import run_pipeline

QUESTIONS_GLOB = [
    r"e:\salah\salah_programing\clinical-decision-support-ref\evaluation_questions\disease\*.json",
    r"e:\salah\salah_programing\clinical-decision-support-ref\evaluation_questions\drug\*.json",
]
N_WARMUP = 2       # Warmup runs (not counted)
N_MEASURE = 20     # Measured runs
SLEEP_BETWEEN = 2  # Avoid rate limits

OUTPUT_PATH = r"e:\salah\salah_programing\clinical-decision-support-ref\latency_results.json"


def load_sample_questions(n=N_MEASURE + N_WARMUP):
    questions = []
    for pattern in QUESTIONS_GLOB:
        for filepath in glob.glob(pattern):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                for q in data:
                    if q.get("question_text", "").strip():
                        questions.append(q["question_text"])
            if len(questions) >= n:
                break
        if len(questions) >= n:
            break
    return questions[:n]


async def measure():
    questions = load_sample_questions()
    if not questions:
        print("ERROR: No questions loaded.")
        return

    print(f"Loaded {len(questions)} questions ({N_WARMUP} warmup + {N_MEASURE} measured)\n")

    latencies = []

    for i, q in enumerate(questions):
        phase = "WARMUP" if i < N_WARMUP else f"RUN {i - N_WARMUP + 1}/{N_MEASURE}"
        print(f"[{phase}] {q[:60]}...", end=" ", flush=True)

        t0 = time.perf_counter()
        try:
            result = await run_pipeline(user_query=q, patient_profile=None, chat_summary=None)
            t1 = time.perf_counter()
            elapsed = t1 - t0

            if i >= N_WARMUP:
                latencies.append(elapsed)
                chunks = result.get("chunks_used", 0)
                print(f"→ {elapsed:.2f}s | chunks={chunks}")
            else:
                print(f"→ {elapsed:.2f}s (warmup)")

        except Exception as e:
            print(f"→ ERROR: {e}")

        if i < len(questions) - 1:
            time.sleep(SLEEP_BETWEEN)

    if not latencies:
        print("\nNo latency data collected.")
        return

    latencies_sorted = sorted(latencies)

    def percentile(data, p):
        idx = max(0, int(len(data) * p / 100) - 1)
        return data[idx]

    p50  = percentile(latencies_sorted, 50)
    p95  = percentile(latencies_sorted, 95)
    p99  = percentile(latencies_sorted, 99)
    mean = statistics.mean(latencies)
    stdev = statistics.stdev(latencies) if len(latencies) > 1 else 0

    print("\n" + "="*60)
    print("LATENCY BENCHMARK RESULTS")
    print("="*60)
    print(f"  Samples:     {len(latencies)}")
    print(f"  Mean:        {mean:.2f}s")
    print(f"  Std Dev:     {stdev:.2f}s")
    print(f"  Min:         {min(latencies):.2f}s")
    print(f"  p50 (median):{p50:.2f}s")
    print(f"  p95:         {p95:.2f}s")
    print(f"  p99:         {p99:.2f}s")
    print(f"  Max:         {max(latencies):.2f}s")

    # Clinical assessment
    print("\n── User Experience Assessment ──")
    if p95 < 5:
        print(f"  ✅ p95 < 5s — Excellent: clinically acceptable response time")
    elif p95 < 10:
        print(f"  ⚠️  p95 < 10s — Acceptable, but consider streaming (already implemented)")
    else:
        print(f"  🔴 p95 > 10s — Slow: optimize retrieval or use smaller model")

    results = {
        "n_samples": len(latencies),
        "mean_s": round(mean, 3),
        "stdev_s": round(stdev, 3),
        "min_s": round(min(latencies), 3),
        "p50_s": round(p50, 3),
        "p95_s": round(p95, 3),
        "p99_s": round(p99, 3),
        "max_s": round(max(latencies), 3),
        "all_latencies": [round(l, 3) for l in latencies],
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(measure())
