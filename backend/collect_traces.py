"""
collect_traces.py
-----------------
Runs the full RAG pipeline on a sample of evaluation questions,
collecting (question, answer, contexts) traces required for RAGAS.

Usage:
    cd clinical-decision-support-ref
    python backend/collect_traces.py

Output:
    evaluation_questions/traces.json
"""
import asyncio
import json
import os
import sys
import glob
import time

sys.path.append(r"e:\salah\salah_programing\clinical-decision-support-ref\backend")
from pipeline import run_pipeline

TRACES_OUTPUT = r"e:\salah\salah_programing\clinical-decision-support-ref\evaluation_questions\traces.json"
QUESTIONS_GLOB = [
    r"e:\salah\salah_programing\clinical-decision-support-ref\evaluation_questions\disease\*.json",
    r"e:\salah\salah_programing\clinical-decision-support-ref\evaluation_questions\drug\*.json",
]
MAX_PER_CATEGORY = 15   # 15 disease + 15 drug = 30 traces total
SLEEP_BETWEEN = 3       # seconds between API calls


def load_questions(patterns, max_per_cat):
    questions = []
    for pattern in patterns:
        cat_qs = []
        for filepath in glob.glob(pattern):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                for q in data:
                    if q.get("question_text", "").strip():
                        cat_qs.append(q)
        questions.extend(cat_qs[:max_per_cat])
    return questions


async def collect():
    questions = load_questions(QUESTIONS_GLOB, MAX_PER_CATEGORY)
    print(f"Loaded {len(questions)} questions to trace.")

    traces = []
    for i, q in enumerate(questions):
        question_text = q["question_text"]
        print(f"[{i+1}/{len(questions)}] {question_text[:70]}...")

        try:
            result = await run_pipeline(
                user_query=question_text,
                patient_profile=None,
                chat_summary=None
            )

            answer = result.get("answer", "")
            sources = result.get("sources", [])

            # Use only chunks that were actually sent to the LLM
            selected_contexts = [
                s["content"]
                for s in sources
                if s.get("is_selected", False) and s.get("content", "").strip()
            ]
            # Fallback: top 4 by score
            if not selected_contexts:
                sorted_sources = sorted(sources, key=lambda x: x.get("score", 0), reverse=True)
                selected_contexts = [s["content"] for s in sorted_sources[:4] if s.get("content")]

            traces.append({
                "question": question_text,
                "answer": answer,
                "contexts": selected_contexts,
                "ground_truth": q.get("ground_truth", ""),
                "question_id": q.get("question_id", f"q_{i}"),
                "target_chunk_ids": q.get("target_chunk_ids", [])
            })
            print(f"  -> OK | answer={len(answer)} chars | contexts={len(selected_contexts)}")

        except Exception as e:
            print(f"  -> ERROR: {e}")
            traces.append({
                "question": question_text,
                "answer": "",
                "contexts": [],
                "ground_truth": "",
                "question_id": q.get("question_id", f"q_{i}"),
                "error": str(e)
            })

        if i < len(questions) - 1:
            time.sleep(SLEEP_BETWEEN)

    os.makedirs(os.path.dirname(TRACES_OUTPUT), exist_ok=True)
    with open(TRACES_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(traces, f, indent=2, ensure_ascii=False)

    successful = sum(1 for t in traces if t.get("answer") and not t.get("error"))
    print(f"\nDone. {successful}/{len(traces)} successful traces saved to: {TRACES_OUTPUT}")


if __name__ == "__main__":
    asyncio.run(collect())
