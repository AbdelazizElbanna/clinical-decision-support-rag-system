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

The Clinical Decision Support RAG System is an advanced medical AI architecture engineered to provide accurate, evidence-based answers to clinical and pharmacological questions. Drawing from a strictly curated knowledge base of Egyptian pharmaceutical data and certified American Academy of Dermatology disease protocols, the system employs rigorous LLM-as-a-judge guardrails to achieve mathematically verified resistance to medical hallucinations and injected noise.

---

## High-Level Architecture Summary

The project operates on a specialized multi-stage data pipeline designed to maintain strict boundaries between data processing and real-time inference.

```text
[Data Sources: AAD HTML & Drug JSONs]
          |
          v
[Data Ingestion Layer: JSON Structuring & Normalization]
          |
          v
[Dynamic Chunking Engine: Semantic vs. Atomic]
          |
          v
[Vector Indexing: Dual-Domain ChromaDB Stores]
   / (Diseases) \            / (Drugs) \
all-MiniLM-L6-v2           BAAI/bge-m3
          |                    |
          v                    v
[FastAPI Backend: Hybrid Retrieval & Cross-Encoder]
          |
          v
[Groq Cloud LLM Generation (Llama-3 / Mixtral)]
          |
          v
[React/Vite Frontend: SSE Streaming & Citation UI]
```

---

## Quick Start & Local Deployment

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

## Comprehensive Master Documentation

For an exhaustive, step-by-step technical breakdown of the ingestion schemas, embedding vector isolation, algorithmic reranker optimization, latency metrics, and 100% Noise Robustness evaluation, please refer to the primary documentation index.

**Read the definitive technical guide here:**
**[docs/MASTER_CLINICAL_RAG_DOCUMENTATION.md](./docs/MASTER_CLINICAL_RAG_DOCUMENTATION.md)**