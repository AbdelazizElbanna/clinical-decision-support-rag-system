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

<div align="center">
  <video src="media/Project-Live-Demo.mp4" width="100%" controls autoplay loop muted>
    Your browser does not support the video tag.
  </video>
</div>

<br />

## Executive Summary & Clinical System Vision

The Clinical Decision Support RAG System was architected to resolve the extreme point-of-care friction experienced by clinicians. Standard medical treatment requires simultaneously cross-referencing complex dermatological symptoms with strict pharmacological contraindications. Traditional Generative AI (LLMs) fundamentally fail at this task due to hallucinations—confidently generating plausible but clinically false drug names, incorrect dosages, or phantom indications. 

In medical environments, the mathematical necessity of zero-hallucination architectures cannot be overstated. A single hallucinated drug interaction can be catastrophic. 

This platform utilizes a dual-domain knowledge base:
1. **American Academy of Dermatology (AAD) Guidelines**: Scraped and structurally normalized treatment paths and differential diagnoses for robust clinical classification.
2. **Egyptian Pharmacological Database**: Local trade names, active ingredients, dosage limits, and regional contraindications dynamically merged from multiple upstream indexes.

By strictly isolating these two domains, the system prevents cross-contamination, ensuring that a semantic search for a symptom does not falsely map to a chemically similar but functionally irrelevant drug compound.

---

## Complete High-Level System Architecture

The project operates on a specialized multi-stage data pipeline designed to maintain strict boundaries between data processing and real-time inference.

```text
[Data Sources: AAD HTML & Egyptian Drug JSONs]
          |
          v
[Data Ingestion Layer: JSON Structuring & Normalization]
          |
          v
[Dynamic Chunking Engine: Semantic Block vs. Atomic Object]
          |
          v
[Vector Indexing: Dual-Domain ChromaDB Stores]
   / (diseases_chroma) \             / (drugs_chroma) \
all-MiniLM-L6-v2 (384-dim)        BAAI/bge-m3 (1024-dim)
          |                                 |
          v                                 v
[FastAPI Backend Gateway: Intent Classification & Router]
(device_utils.py hardware routing)
          |
          v
[Clinical Safety Guardrails Layer (LLM-as-a-judge)]
          |
          v
[Groq Cloud LLM Generation (Llama-3 / Mixtral)]
          |
          v
[React/Vite Frontend: Server-Sent Events (SSE) streaming]
```

### Technical Layer Responsibility
*   **React + Vite Frontend**: Delivers a high-performance clinical dashboard with interactive citation drawers for real-time evidence verification.
*   **FastAPI Backend Gateway**: Manages state, routes traffic, and dynamically evaluates GPU compute capability via `device_utils.py` to ensure safe hardware fallback.
*   **Intent Classification & Router**: An LLM-based gatekeeper that parses ambiguous colloquial queries, standardizes medical terms, and determines whether to search the Disease DB, Drug DB, or both.
*   **Dual ChromaDB Vector Stores**: Physically segregates knowledge spaces to allow domain-specific embeddings (`BAAI/bge-m3` for complex local drug names and `all-MiniLM-L6-v2` for English clinical prose).
*   **Groq Cloud LLM Generation**: Executes rapid generation using Llama-3/Mixtral while strictly adhering to retrieved context.
*   **Clinical Safety Guardrails**: Enforces an "abstain if absent" policy, refusing to generate answers if the Vector DB returns low-confidence scores.

---

## Comprehensive Setup & Installation Guide

To deploy the project locally on your machine, follow these steps strictly in order.

### 1. Environment Prerequisites
- **Python 3.10+** (Required for the FastAPI Backend)
- **Node.js 18+** (Required for the React Frontend)
- **CUDA / GPU Drivers** (Optional, `device_utils.py` automatically falls back to CPU if capability checks fail)
- **Groq API Key** (Required for the LLM inference engine)

### 2. Backend Setup
1. Open a terminal and navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up the API Keys by creating a `.env` file inside the `backend/` directory:
   ```env
   GROQ_API_KEY=gsk_your_api_key_here
   ```
5. Start the backend server:
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```
   *(The backend API is now actively listening at `http://localhost:8000`)*

### 3. Frontend Setup
1. Open a new terminal window and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install the required Node modules:
   ```bash
   npm install
   ```
3. Start the frontend development server:
   ```bash
   npm run dev
   ```
   *(The Clinical Decision Support interface is accessible at `http://localhost:5173`)*

### 4. Verification
- The backend should display `Device validation successful` or `Falling back to cpu` in the console on boot.
- Verify vector storage health by querying the chat interface. If context sources appear in the UI, ChromaDB is active.

---

## Comprehensive Master Documentation

For an exhaustive, step-by-step technical breakdown of the ingestion schemas, embedding vector isolation, algorithmic reranker optimization, latency metrics, and 100% Noise Robustness evaluation, please refer to the primary documentation index.

**Read the definitive technical guide here:**
**[docs/MASTER_CLINICAL_RAG_DOCUMENTATION.md](./docs/MASTER_CLINICAL_RAG_DOCUMENTATION.md)**