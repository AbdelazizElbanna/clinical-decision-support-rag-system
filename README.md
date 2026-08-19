<h1 align="center">Clinical Decision Support RAG System</h1>

<p align="center">
  <strong>An end-to-end clinical knowledge retrieval and decision support pipeline powered by custom schema-aware chunking, domain-specific embeddings, and high-precision hybrid retrieval.</strong>
</p>

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
  <img src="https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch" />
  <img src="https://img.shields.io/badge/Evaluation-RAGAS-green?style=for-the-badge" alt="Evaluation" />
</div>

<br />

The Clinical Decision Support RAG System is an advanced medical AI architecture engineered to provide accurate, evidence-based answers to clinical and pharmacological questions. Drawing from a strictly curated knowledge base of regional pharmaceutical data and certified dermatological disease protocols, the system employs rigorous LLM-as-a-judge guardrails to achieve **mathematically verified resistance to medical hallucinations and injected noise**.

This system is built for uncompromising clinical safety, ensuring high-speed access to reliable differential diagnostics and cross-checking contraindications without the risks associated with standard generative AI pipelines.

---

## Tech Stack & Infrastructure

<p align="center">
  <img src="https://img.shields.io/badge/LangChain-121212?style=for-the-badge&logo=chainlink&logoColor=white" alt="LangChain" />
  <img src="https://img.shields.io/badge/ChromaDB-FF6B6B?style=for-the-badge&logo=databricks&logoColor=white" alt="ChromaDB" />
  <img src="https://img.shields.io/badge/Scikit--Learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white" alt="Scikit-Learn" />
  <img src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas" />
  <img src="https://img.shields.io/badge/Groq_Cloud-000000?style=for-the-badge" alt="Groq Cloud" />
  <img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind CSS" />
</p>

---

## Key System Capabilities

* **Dual-Domain Knowledge Base**: Independent indexing and retrieval pipelines for Dermatology (Diseases) and Pharmacology (Drugs) to maximize embedding separation and context relevance.
* **Zero-Hallucination Guardrails**: Adheres to strict evidence-grounding constraints. Evaluated to a perfect 1.0 (100%) score in Faithfulness and Noise Robustness.
* **Intent-Driven Query Rewriting**: Employs an LLM-based Intent Extractor to standardize complex, vague, or colloquial Arabic clinical queries into precise English search constraints, actively increasing Hit Rate by +5.0%.
* **High-Speed SSE Streaming**: Architected with Server-Sent Events (SSE) to drop perceived latency (Time-To-First-Token) to under 1 second.
* **Ground-Truth Citation Tracking**: Automates deep provenance mapping directly from scraped source data to the generated response, delivering transparent evidence URLs to clinicians.

---

## End-to-End System Architecture

The project operates on a specialized multi-stage data pipeline designed to maintain strict boundaries between data processing and real-time inference.

1. **Data Ingestion & Structuring**: 
   Raw clinical HTML documentation and complex upstream pharmaceutical datasets are programmatically scraped, cleaned, and condensed into flat, lightweight JSON objects. Crucially, exact `sources_summary` provenance tracking is embedded at the root of every parsed object.
2. **Dynamic Chunking & Indexing**: 
   The system abandons generic character-based chunking. It utilizes *schema-aware semantic chunking* for disease protocols (preserving full symptom trees) and *object-level atomic chunking* for pharmaceuticals, ensuring vital warnings are never separated from their active ingredients.
3. **Domain-Specific Embeddings**: 
   High-dimensional vector embeddings are computed utilizing `all-MiniLM-L6-v2` (Diseases) and `BAAI/bge-m3` (Drugs), and pushed into independent ChromaDB spaces.
4. **Hybrid RAG Retrieval Engine**: 
   At query time, the system rewrites the prompt, isolates the clinical intent, and queries the targeted database. Cross-encoder reranking is dynamically bypassed for complex pharmacological trade names to preserve vector precision.
5. **Clinical Interface**: 
   A high-performance React web application provides clinicians with real-time text streaming, interactive citations, and integrated PDF export capabilities.

---

## Benchmark Performance & Evaluation Highlights

The system was subjected to an aggressive adversarial evaluation suite designed to test hallucination resistance via injected medical noise. Following architectural optimizations, the system meets or exceeds all operational safety targets.

| Evaluation Metric | Target Threshold | Measured Result | Operational Status |
| :--- | :--- | :--- | :--- |
| **Faithfulness (RAGAS)** | > 0.95 | **1.0 (100%)** | Passed |
| **Noise Robustness** | > 0.95 | **1.0 (100%)** | Passed |
| **Hit Rate@10** | > 90.0% | **93.3%** (Disease) / **92.0%** (Drug) | Passed |
| **MRR@10** | > 0.70 | **0.74** (Disease) / **0.83** (Drug) | Passed |
| **Answer Relevance** | > 4.0 / 5.0 | **4.8 / 5.0** (LLM Judge) | Passed |
| **Latency (TTFT)** | < 5s | **< 1s** (SSE Streaming) | Passed |

> *Note: By achieving 100% Noise Robustness, the system successfully ignored completely plausible but entirely fake medical context injected directly into its retrieval stream, refusing to generate unsupported claims.*

---

## Repository Directory Structure

```text
clinical-decision-support-rag-system/
├── backend/                  # FastAPI server, RAG engine, and SSE endpoints
├── frontend/                 # React UI, Vite, custom Tailwind styling
├── src/                      # Data pipeline: Scraping, Ingestion, and Embeddings
├── data/
│   ├── raw/                  # Flat, lightweight JSON databases (Diseases & Drugs)
│   ├── Chunked_Data/         # Processed LangChain documents ready for vectorization
│   └── vectorstores/         # ChromaDB collections (drugs_chroma, diseases_chroma)
├── docs/                     # Comprehensive reports and architectural documentation
├── evaluation_questions/     # Test cases and clinical queries for the pipeline
├── evaluation_results/       # Output logs and artifacts from the evaluation scripts
├── requirements.txt          # Consolidated Python dependencies
└── SETUP_GUIDE.md            # Detailed setup instructions
```

---

## Quick Setup & Local Deployment

To deploy the entire stack locally, follow these steps. For an extended deployment breakdown, consult the [Setup Guide](./SETUP_GUIDE.md).

### 1. Repository & Dependencies
Clone the repository and install the backend environment:
```bash
cd backend
pip install -r ../requirements.txt
```

### 2. Environment Configuration
Establish your LLM routing layer by creating a `.env` file inside the `backend/` directory:
```env
GROQ_API_KEY=gsk_your_api_key_here
```

### 3. Run the Backend API
Initiate the FastAPI Uvicorn server:
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
*The API is now actively listening at `http://localhost:8000`.*

### 4. Run the Frontend Clinical UI
Open a secondary terminal, initialize the React environment, and launch Vite:
```bash
cd frontend
npm install
npm run dev
```
*The Clinical Decision Support interface is accessible at `http://localhost:5173`.*

---

## Comprehensive Documentation Index

For deep technical dives into the engineering decisions, evaluation architecture, and historical experiments, please review the specialized documentation located in the `docs/` directory:

1. [**Data Pipeline & Embeddings Technical Guide**](./docs/data_pipeline_and_embeddings.md) - Deep dive into data structuring, custom chunking algorithms, and embedding logic.
2. [**Final Retrieval Evaluation Report**](./docs/final_retrieval_evaluation_report.md) - Exhaustive RAGAS metrics, Cross-Encoder latency analysis, and Hallucination robustness breakdown.
3. [**Pipeline Refactoring & Audit Log**](./docs/pipeline_refactoring_report.md) - System audit verifying RAG ground-truth citation reliability and data cleanliness.
4. [**Evaluation Metrics Guide**](./docs/evaluation_metrics_guide.md) - The mathematical reasoning underpinning our retrieval scoring strategy.
5. [**Experiments Log (English)**](./docs/EXPERIMENTS_LOG_EN.md) - Engineering log detailing the 14 major system challenges resolved during development.
6. [**Question Dataset Analysis Report**](./docs/question_dataset_analysis_report.md) - Categorical breakdown of the adversarial queries used to benchmark the system.