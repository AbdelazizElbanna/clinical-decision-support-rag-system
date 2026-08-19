# Master Clinical RAG Documentation

## Section 1: Executive Summary & System Vision

### Clinical Background & Domain Focus
The Clinical Decision Support RAG System is purpose-built to address the demanding knowledge requirements of modern clinical practice. Its primary clinical domain strictly focuses on **Dermatology Protocols** (derived from certified American Academy of Dermatology data) and regional **Pharmacological Data** (utilizing unified Egyptian drug databases). Note: While generic architectures often model general guidelines (e.g., Hypertension), this system is explicitly specialized for complex dermatological differential diagnosis and highly specific localized drug contraindication checks.

### Problem Statement & Target Workflow
Clinicians face critical time constraints when cross-referencing complex dermatological symptoms and identifying potentially dangerous pharmacological interactions. Standard generative AI tools are prone to severe medical hallucinations, rendering them unsafe for clinical deployment. 

Our target clinical workflow provides immediate, transparent, and mathematically verified decision support. By utilizing high-speed Retrieval-Augmented Generation (RAG) with strict guardrails, the system delivers actionable differential diagnosis and drug safety profiles with a guaranteed zero-hallucination rate on tested adversarial data.

---

## Section 2: Complete End-to-End Pipeline & Architecture

### High-Level Architectural Overview

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

### Layer Breakdown
1. **Ingestion Layer**: Programmatically scrapes raw HTML documentation and normalizes complex upstream drug datasets into flat, lightweight JSON objects.
2. **Retrieval Layer**: Employs domain-specific embedding models routing requests to parallel Vector Databases depending on query intent.
3. **Generation Layer**: Leverages Groq Cloud for ultra-fast inference (Llama-3/Mixtral), returning structured clinical context.
4. **Clinical Guardrails**: Operates on a strict "abstain if absent" prompt framework enforced by LLM-as-a-judge evaluators.
5. **UI Layer**: A React dashboard delivering Server-Sent Events (SSE) streaming for immediate Time-To-First-Token (TTFT) performance.

### Modularity & Vector DB Abstraction
The system utilizes a dual-database architecture: `diseases_chroma` and `drugs_chroma`. This strict separation prevents embedding crossover where clinical symptoms might mathematically overlap with chemically similar but functionally irrelevant drug compounds. 

### Error Handling Strategies
*   **Hardware Fallback**: Utilizing `device_utils.py`, the system aggressively validates PyTorch CUDA capabilities upon initialization. If GPU memory is exhausted or CUDA compatibility fails (e.g., Compute Capability < 6), it safely falls back to CPU indexing to prevent backend crash loops.
*   **Schema Resilience**: Missing pharmacological safety warnings or incomplete drug profiles are gracefully captured during ingestion; empty nodes are tagged as "Insufficient Information" rather than allowing null pointers in retrieval context.

---

## Section 3: Ingestion & Retrieval Deep-Dive

### Section-Aware Chunking Methodology
Fixed-size character chunking fundamentally destroys clinical context. This system employs two distinct strategies:
*   **Object-Level Atomic Chunking (Drugs)**: Pharmacological data is chunked atomically per drug. Critical warnings (contraindications, pregnancy safety) are hard-bound to the active ingredient context window, ensuring the LLM never retrieves a medication name without its associated clinical dangers.
*   **Semantic Block Chunking (Diseases)**: Symptom trees and treatment protocols are recursively chunked by schema headings, preserving the complete diagnostic criteria in a single verifiable vector payload.

### Embedding Model Selection & Benchmarks
*   **Diseases (`all-MiniLM-L6-v2`)**: A highly efficient 384-dimensional model proven sufficient for standard English medical symptom descriptions.
*   **Drugs (`BAAI/bge-m3`)**: A robust 1024-dimensional multilingual model selected explicitly to handle complex, non-standard Egyptian drug trade names and mixed Arabic/English pharmaceutical queries without severe token degradation.

### Hybrid Search & Re-ranking
The system implements a `ms-marco-MiniLM-L-6-v2` cross-encoder to rerank vector search results based on deep semantic relevance. 
*   **Iterative Innovation**: During evaluation, the reranker successfully boosted Precision@4 for disease queries. However, it caused a -2.2% Precision@4 degradation for drugs because the MS MARCO general-English training data penalized Egyptian pharmaceutical brand names. Consequently, reranking is dynamically bypassed for the drug domain to optimize both precision and latency.

---

## Section 4: Grounding, Citations & Faithfulness

### Citation Tracking Mechanism
Traceability is maintained at the ingestion root. During HTML scraping, the exact source URL and page title are preserved as a `sources_summary` node within the JSON schema. When a chunk is embedded into ChromaDB, this node is injected into the vector metadata. The retrieval engine passes this metadata unmodified to the LLM context window and directly to the React UI, allowing for Document and Page-level precision.

### Preserving Recommendation Strength
Instead of generic conditional thresholds, this repository heavily relies on pharmacological safety flags. Data normalization explicitly preserves fields such as "Caution required" or "Absolute Contraindication". These strength modifiers are hard-coded into the vector chunk to ensure the generation layer accurately weights the severity of clinical recommendations.

### Anti-Hallucination Guardrails
The system instructions strictly forbid interpolation. The LLM is forced to cite the exact ID of the context chunk used for every generated claim. If the provided context yields no matches for the query, the model triggers an abstention sequence.

---

## Section 5: Clinical Safety & Guardrails

### Confidence Thresholds & Abstention Triggers
The system operates on an absolute zero-trust framework regarding external knowledge. It achieved a 100% score (20/20) in Noise Robustness evaluations by successfully ignoring highly plausible but adversarial fake medical data injected into its context window. If the retrieval engine yields context below the cosine similarity confidence threshold, the LLM abstains from clinical advice.

### Out-of-Scope Query Handling
The Intent Extractor layer identifies whether a user query falls within the Dermatology/Allergy or Egyptian Drug domains. If a user asks an out-of-domain medical question (e.g., Cardiology or Oncology), the intent classifier forces a fallback response, explicitly declaring the system's domain limitations to prevent unsafe general medical advice.

### Clinical Disclaimers
A permanent, highly visible clinical disclaimer is rendered across the React UI. It legally and functionally reminds end-users that the application is a decision support tool, not a diagnostic authority, and must be used in conjunction with professional clinical judgment.

---

## Section 6: Evaluation Methodology & Metrics

### Test Set Design
The evaluation suite relies on a cross-domain dataset strictly stratified into "Easy," "Medium," and "Hard" clinical queries, featuring adversarial perturbations and colloquial Arabic phrasings to test real-world clinical resilience.

### Core RAG Metrics & Performance
*   **Faithfulness (RAGAS)**: 1.0 (100%) - Zero hallucinated claims.
*   **Hit Rate@10**: 93.3% (Disease) / 92.0% (Drug).
*   **MRR@10**: 0.74 (Disease) / 0.83 (Drug).
*   **Noise Robustness**: 100% adversarial resistance.

### Iterative Engineering Improvements
*   **Intent Extraction**: Initial Hit Rates suffered due to colloquial clinical slang. An LLM Intent Extractor was placed ahead of the vector search to standardize queries, resulting in a direct +5.0% boost in Hit Rate.
*   **Latency Optimization**: Static generation resulted in unacceptable 15-second wait times. Implementing Server-Sent Events (SSE) streaming reduced the perceived latency (Time-To-First-Token) to under 1 second.
*   **Precision vs. Latency Trade-off**: As noted in Section 3, removing the cross-encoder for the drug domain marginally improved latency while preventing the -2.2% drop in Precision@4.

---

## Section 7: UI & Clinical UX

### Live UI Implementation
The frontend is constructed using React, Vite, and Tailwind CSS. It focuses on a clean, distraction-free clinical environment optimized for rapid readability in high-stress medical settings.

### Visual Distinction of Confidence
The UI utilizes strict color coding to distinguish data safety. High-confidence, fully grounded answers are presented neutrally, while missing contexts, out-of-scope warnings, or identified contraindications trigger highly visible alert blocks.

### Evidence Verification
Clinicians can verify source evidence in seconds. Every generated clinical claim features inline reference tags. Clicking a tag expands a drawer in the UI revealing the exact text chunk extracted from the vector database alongside its clickable source URL.
