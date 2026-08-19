"""
ragas_evaluator.py
------------------
Reads traces.json (collected by collect_traces.py) and runs RAGAS metrics:
  - Faithfulness
  - Answer Relevance
  - Context Precision
  - Context Recall (only when ground_truth is provided)

Usage:
    python backend/ragas_evaluator.py

Requirements:
    pip install ragas langchain-groq datasets
"""
import json
import os
import sys
from datasets import Dataset

sys.path.append(r"e:\salah\salah_programing\clinical-decision-support-ref\backend")

# ── RAGAS imports ──────────────────────────────────────────────────────────────
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
from config import GROQ_API_KEYS, LLM_MODEL

TRACES_PATH = r"e:\salah\salah_programing\clinical-decision-support-ref\evaluation_questions\traces.json"
RESULTS_OUTPUT = r"e:\salah\salah_programing\clinical-decision-support-ref\ragas_results.json"

# ── Load traces ────────────────────────────────────────────────────────────────
print("Loading traces...")
with open(TRACES_PATH, "r", encoding="utf-8") as f:
    traces = json.load(f)

# Filter: only traces with non-empty answer and contexts
valid_traces = [
    t for t in traces
    if t.get("answer", "").strip()
    and t.get("contexts")
    and len(t["contexts"]) > 0
]
print(f"Valid traces for evaluation: {len(valid_traces)} / {len(traces)}")

# Build HuggingFace Dataset
has_ground_truth = any(t.get("ground_truth", "").strip() for t in valid_traces)
print(f"Ground truth available: {has_ground_truth}")

data = {
    "question": [t["question"] for t in valid_traces],
    "answer":   [t["answer"] for t in valid_traces],
    "contexts": [t["contexts"] for t in valid_traces],
}
if has_ground_truth:
    data["ground_truth"] = [t.get("ground_truth", "") for t in valid_traces]

dataset = Dataset.from_dict(data)

# ── Configure LLM (Groq) and Embeddings ────────────────────────────────────────
print(f"\nUsing LLM: {LLM_MODEL}")
print("Using embeddings: all-MiniLM-L6-v2 (local)")

# Use first available Groq key
groq_llm = ChatGroq(
    api_key=GROQ_API_KEYS[0],
    model_name="llama3-70b-8192",   # Use a capable model for the judge
    temperature=0
)
llm_wrapper = LangchainLLMWrapper(groq_llm)

hf_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
embeddings_wrapper = LangchainEmbeddingsWrapper(hf_embeddings)

# ── Choose metrics ─────────────────────────────────────────────────────────────
metrics = [faithfulness, answer_relevancy, context_precision]
if has_ground_truth:
    metrics.append(context_recall)
    print("Including Context Recall (ground_truth found).")
else:
    print("Skipping Context Recall (no ground_truth provided).")

# ── Run RAGAS ─────────────────────────────────────────────────────────────────
print("\nRunning RAGAS evaluation (this may take a few minutes)...\n")
result = evaluate(
    dataset=dataset,
    metrics=metrics,
    llm=llm_wrapper,
    embeddings=embeddings_wrapper,
    raise_exceptions=False,
)

# ── Print Results ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("RAGAS EVALUATION RESULTS")
print("="*60)
result_dict = result.to_pandas().mean(numeric_only=True).to_dict()
for metric, score in result_dict.items():
    emoji = "🟢" if score >= 0.85 else "🟡" if score >= 0.70 else "🔴"
    print(f"  {emoji} {metric:<30}: {score:.4f}")

# Clinical assessment
print("\n── Medical Safety Assessment ──")
faith_score = result_dict.get("faithfulness", 0)
if faith_score >= 0.95:
    print("  ✅ Faithfulness EXCELLENT - LLM is NOT hallucinating.")
elif faith_score >= 0.80:
    print("  ⚠️  Faithfulness GOOD but below medical threshold (target: 0.95).")
else:
    print("  🚨 Faithfulness CRITICAL - LLM is generating unsupported claims!")

# ── Save Results ──────────────────────────────────────────────────────────────
output = {
    "summary": result_dict,
    "per_question": result.to_pandas().to_dict(orient="records"),
    "total_traces_evaluated": len(valid_traces)
}
with open(RESULTS_OUTPUT, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print(f"\nFull results saved to: {RESULTS_OUTPUT}")
