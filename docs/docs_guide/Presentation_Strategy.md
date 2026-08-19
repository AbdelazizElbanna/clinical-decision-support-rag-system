# 🎤 Hackathon Presentation Strategy: MedLens AI

This guide is designed to map perfectly to the **Hackathon Evaluation Rubric** (Retrieval Quality 30%, Grounding 25%, System Architecture 15%, Evaluation 15%, Safety & UX 15%). 

## 🏆 Core Philosophy to Emphasize (The "Hook")
Start strong by saying: *"Fluent Answer ≠ Safe Answer. In dermatology, hallucinations are dangerous. MedLens AI is built entirely around clinical grounding, traceability, and verifiable refusal."*

---

## 📑 Optimal Slide Flow & Talking Points

### Slide 1: The Problem & Scope (1 minute)
*   **What to say:** Generic LLMs answer from parametric memory—they sound confident but hallucinate. We built a RAG system tightly scoped to Dermatology (Eczema, Psoriasis, Urticaria) for the Egyptian demographic.
*   **Highlight:** We only ingest official, public guidelines (WHO, NICE, local protocols). No private data. 

### Slide 2: End-to-End Architecture (1 minute)
*   **What to say:** Show the modular pipeline. 
*   **Key Flex (System Architecture 15%):** 
    *   Explain how the **Intent Extractor** acts as a brain: it tracks conversation history, standardizes drug names, and detects if the query came from Voice (STT) to make the LLM tolerant of misspellings.
    *   Highlight the **Weather API Integration**: The system actively fetches UV Index and Humidity to contextualize environmental triggers.

### Slide 3: Retrieval Quality & Precision (1 minute)
*   **What to say:** This is where we win the technical points.
*   **Key Flex (Retrieval Quality 30%):**
    *   We use `BAAI/bge-m3` for robust Arabic/English cross-lingual embeddings.
    *   We implemented a **Cross-Encoder Reranker** (`ms-marco-MiniLM-L-6-v2`) which re-scores the Top-15 chunks against the query to fetch the absolute Top-5. This maximizes our `Precision@K`.

### Slide 4: Grounding, Citations & Safety (1 minute)
*   **What to say:** The LLM is a synthesizer, not a doctor.
*   **Key Flex (Grounding 25% & Safety 15%):**
    *   The LLM is forced to format responses with exact `[Source N]` markdown citations.
    *   Show the **Evidence Panel (SourceCard)**: Every claim traces back to a visible chunk and URL. Transparency builds trust.
    *   Explain the **Safe Refusal Logic**: If the chunks lack the answer, the system defaults to: *"The retrieved sources do not provide enough information..."*

### Slide 5: The Demo & UX Excellence (1 minute)
*   **What to say:** Clinical tools must be accessible.
*   **Key Flex (Safety & UX 15%):**
    *   Show the **Voice Integration (Whisper STT)**.
    *   Demonstrate the **Karaoke-style Text-to-Speech (TTS)** using Edge Neural TTS. Emphasize how we engineered asynchronous chunked pre-fetching so playback starts instantly (Zero TTFB latency).

---

## 💻 Live Demo Script (The "Show, Don't Tell" Phase)

Follow the 3 cases requested in the rubric:

1.  **CASE A (Success / Direct Query):**
    *   *Action:* Ask: "ما هو علاج الصدفية الخفيفة؟" (What is the treatment for mild psoriasis?)
    *   *Point to make:* Show the structured answer, the `[Source N]` tags, and open the Evidence Panel to show the exact chunk used.

2.  **CASE B (Complex Multi-step):**
    *   *Action:* Use Voice (Microphone): *"أنا عندي إكزيما والجو حر النهاردة، هل أقدر أخرج؟"* (I have eczema and it's hot today, can I go out?)
    *   *Point to make:* Show how the Intent Extractor caught the weather context, triggered the Weather API, retrieved the UV index, and synthesized it with Eczema guidelines. Click the "Listen" button to show off the TTS Karaoke highlighting.

3.  **CASE C (Safe Refusal):**
    *   *Action:* Ask something out of scope or highly specific: *"What is the exact dosage of chemotherapy for Stage 4 Melanoma?"*
    *   *Point to make:* Show how the system **refuses** to answer confidently because it lacks the retrieved context, prioritizing safety over fluency.

---


---

## 🎯 Pro-Tips for the Q&A
*   **If asked about "Evaluation Depth (15%)":** Quote the actual results: Faithfulness 100%, Noise Robustness 100% (20/20 cases), Context Precision 100%, Answer Relevance 83.4%, Reranker Precision@4 +8.96%, and LLM-Judge scores of 5.0/5.0 across all dimensions. Mention `llm_judge.py` and `dermatology_ai_test_suite.md` as the evaluation framework.
*   **If asked about latency:** TTFT (Time-to-First-Token) is < 1s via SSE streaming. Full response median is ~15s — normal for RAG with reranking. Emphasize that our Karaoke TTS chunking makes the UX feel instant since it reads while generating.
