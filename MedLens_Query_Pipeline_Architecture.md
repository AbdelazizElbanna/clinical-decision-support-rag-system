# MedLens AI — Query Pipeline Architecture

Trace of a single user query from HTTP request to streamed response.

---

## Flow Diagram

```
Client
  │
  ▼
POST /api/query  or  /api/query/stream           [main.py]
  │  (user_query, patient_profile, chat_summary)
  ▼
extract_intent()                                  [intent_extractor.py]
  │  → is_medical_query, condition, collections_to_query,
  │    governorate, requires_weather, medications,
  │    clinical_summary, search_query_en
  ▼
┌─────────────────────────┐
│  is_medical_query?      │
└─────────────────────────┘
   │ false                        │ true
   ▼                              ▼
Direct LLM reply          fetch_weather()                    [weather_service.py]
(no retrieval,             (if requires_weather)
 no RAG)                          │
   │                              ▼
   │                       retrieve()                         [retriever.py]
   │                        │  query = user_query (raw)
   │                        │  → 20 candidates (diseases) / 10 (drugs)
   │                        │    per collection
   │                        ▼
   │                       CrossEncoder rerank                [pipeline.py]
   │                        │  (skipped for 'drugs' collection)
   │                        │  score → randomized min-max normalize
   │                        │  drop score < 0.25, keep top 4/collection
   │                        ▼
   │                       Build context
   │                        │  patient profile → clinical summary →
   │                        │  weather block → [Source N] chunks →
   │                        │  medication context
   │                        ▼
   │                       Assemble prompt
   │                        │  SYSTEM_PROMPT + full_context +
   │                        │  [PATIENT QUERY] + language instruction
   │                        ▼
   └──────────────────► groq_router.py
                          │  round-robin across API key pool
                          │  on rate-limit/failure → next key
                          ▼
                        Groq LLM generation
                          │  (streamed for /stream endpoint)
                          ▼
                        Response + pipeline_trace + sources[]
                          │
                          ▼
                        Client
                         (PipelineTrace.jsx renders trace + sources)
```

---

## Stage Breakdown

### 1. Entry — `main.py`
`POST /api/query` (or the streaming variant `/api/query/stream`) accepts the raw query string, the caller's `patient_profile` (age, gender, notes), and `chat_summary` (multi-turn working memory). Delegates immediately to `run_pipeline()` / `run_pipeline_stream()` in `pipeline.py`.

### 2. Intent Extraction — `intent_extractor.py`
A dedicated LLM call structures the raw query into:

| Field | Purpose |
|---|---|
| `is_medical_query` | routes to RAG path or direct-reply path |
| `condition` | Eczema / Psoriasis / Urticaria / Unknown |
| `collections_to_query` | which vector collections to hit |
| `governorate` | for weather lookup |
| `requires_weather` | gate for weather enrichment |
| `medications_current` / `medications_new` | drug-context injection |
| `clinical_summary` | rolling conversation memory |
| `search_query_en` | translated/cleaned English query — **generated here, not consumed downstream** |

### 3. Routing Fork
- **Non-medical** (`is_medical_query: false`): short-circuits to a direct LLM reply. Language (Arabic/English) picked via a Unicode range check on the raw query. No retrieval, no weather, no RAG — returns immediately.
- **Medical**: proceeds through the full pipeline below.

### 4. Weather Enrichment — `weather_service.py`
Runs only if `requires_weather` is true and a governorate was extracted. Resolves governorate → lat/lon, fetches live temperature, humidity, UV index, wind speed, dust, and PM2.5.

### 5. Retrieval — `retriever.py`
`retrieve(query=user_query, ...)` queries the relevant Chroma collections:
- Diseases (`medical_guidelines`) — encoded with `all-MiniLM-L6-v2`
- Drugs — encoded with `BAAI/bge-m3`

Candidate count is hardcoded inside `retriever.py` (20 for diseases, 10 for drugs) regardless of the `n_per_collection` argument passed from `pipeline.py`.

> Note: retrieval is called with `user_query` (raw), not `search_query_en` (the translated/cleaned query from step 2). The rewritten query is computed but not used in this call path.

### 6. Reranking & Scoring — `pipeline.py`
For every collection except `drugs`:
- A cross-encoder (`ms-marco-MiniLM-L-6-v2`) scores each candidate against the query.
- Raw scores are min-max normalized into a randomized band (`bottom_target` ≈ 0.05–0.15, `top_target` ≈ 0.85–0.95) rather than passed through as-is.

Chunks scoring below `0.25` are dropped. Remaining chunks are deduped by exact text match and capped at 4 per collection (`k_selected_per_collection`).

### 7. Context Assembly
Context blocks are concatenated in this fixed order:
1. `[PATIENT PROFILE]` — age, gender, notes
2. `[CONVERSATION CONTEXT]` — working memory / clinical summary
3. `[WEATHER CONTEXT]` — live metrics, if fetched
4. `[Source N — Source: url]` — one block per selected chunk
5. `[MEDICATION CONTEXT]` — current/considered medications

### 8. Prompt Construction
Final prompt = `SYSTEM_PROMPT` (grounding rules, refusal phrase, output format) + `full_context` + `[PATIENT QUERY]` + a mandatory language instruction (Arabic or English, same Unicode check as step 3).

### 9. Generation — `groq_router.py`
Prompt sent to Groq. The router holds a pool of API keys and rotates to the next one on rate-limit or failure. Streaming endpoint yields tokens incrementally; non-streaming endpoint returns the full completion.

### 10. Response Packaging
Returns three things to the client:
- The generated answer text
- `sources[]` — every candidate chunk (selected or not), with score, section, url, and selection status
- `pipeline_trace` — structured record of intent, weather, retrieval, and generation metadata, consumed by `PipelineTrace.jsx` to render the evidence panel

---

## Key Files

| File | Role |
|---|---|
| `backend/main.py` | HTTP entrypoints |
| `backend/pipeline.py` | orchestration, reranking, prompt assembly |
| `backend/intent_extractor.py` | query → structured intent |
| `backend/retriever.py` | vector search against Chroma |
| `backend/weather_service.py` | governorate → live weather |
| `backend/groq_router.py` | LLM call + key failover |
| `frontend/src/components/PipelineTrace.jsx` | renders the evidence panel from `pipeline_trace` + `sources[]` |
