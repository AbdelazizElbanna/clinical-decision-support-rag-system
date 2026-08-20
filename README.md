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