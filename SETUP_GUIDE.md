# 🏥 Skin Health AI (Clinical Decision Support RAG System)

An advanced Retrieval-Augmented Generation (RAG) system designed to support clinical decision-making in dermatology and pharmacology. The system integrates a massive medical database (Egyptian drugs + dermatology diseases) with AI models to provide documented, accurate, and evidence-based answers, completely free from hallucinations.

---

## 📂 Project Structure

The project is divided into 3 main components:
1. **`backend/`**: The FastAPI server responsible for the RAG engine, vector databases (ChromaDB), LLM routing, and report generation.
2. **`frontend/`**: The React + Vite user interface, designed interactively to support chat and real-time SSE streaming.
3. **`docs/`**: The documentation folder containing evaluation reports, experiment logs, and the original data pipeline technical guide.

---

## 🚀 Setup & Getting Started Guide

To set up and run the project locally on your machine, follow these steps in order:

### 1️⃣ Prerequisites
- **Python 3.10+** (Required for the Backend)
- **Node.js (v18+)** (Required for the Frontend)
- **Groq API Key** (Required to run the LLM inference engine)
- **PrinceXML** *(Optional)*: Required if you want to use the "Export Chat as PDF" feature. You can download it from the [Official Website](https://www.princexml.com/download/).

### 2️⃣ Backend Setup

1. Open a terminal and navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up the API Keys:
   - Open or create a `.env` file inside the `backend/` directory.
   - Add your Groq API key to the file:
     ```env
     GROQ_API_KEY=gsk_your_api_key_here
     ```
4. Start the backend server:
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```
   *(The API will now be running at `http://localhost:8000`)*

### 3️⃣ Frontend Setup

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
   *(The UI will typically be accessible at `http://localhost:5173`)*

---

## 📚 Documentation & Reports

All architectural details, evaluation reports, and experiments we conducted are available in the `docs/` folder. **We highly recommend reading them to understand the system's robustness:**

1. [**Experiments Log (AR)**](./docs/EXPERIMENTS_LOG.md): Documents the 14 engineering challenges we faced and solved (e.g., SSE Streaming, Reranker Bypass, Few-Shot Prompting).
2. [**Experiments Log (EN)**](./docs/EXPERIMENTS_LOG_EN.md): A professional English translation of our experiments log.
3. [**Final Evaluation Report**](./docs/final_retrieval_evaluation_report.md): Contains the final RAGAS metrics for Retrieval Hit Rate and Hallucination robustness.
4. [**Evaluation Metrics Guide**](./docs/evaluation_metrics_guide.md): A scientific explanation of how we evaluated the system and why we used RAG metrics instead of traditional classification metrics.
5. [**Data Pipeline Documentation**](./README.md): The original guide on how data was scraped, cleaned, chunked, and embedded into the Vector DB.

---

## 🛠️ Tech Stack
- **Backend:** FastAPI, Python, LangChain, SentenceTransformers, Cross-Encoder
- **Vector Database:** ChromaDB (bge-m3 for Drugs, all-MiniLM for Diseases)
- **Frontend:** React, Vite, Tailwind CSS (Custom Design System), SSE Streaming
- **LLM Engine:** Groq Cloud (Llama-3 / Mixtral depending on availability)
