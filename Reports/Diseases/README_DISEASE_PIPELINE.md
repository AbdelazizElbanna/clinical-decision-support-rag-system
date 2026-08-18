# Disease RAG Data Pipeline

## 1. Overview
This document provides a complete technical description of the disease data pipeline for the clinical decision support RAG system. It documents the exact lifecycle of disease data from raw HTML extraction through chunking, processing into retrieval-ready chunks, and embedding into ChromaDB using the `all-MiniLM-L6-v2` embedding model. It establishes the structure and evaluation strategy for the resulting knowledge base of dermatological conditions.

## 2. Dataset Lifecycle
The data processing pipeline follows these sequential stages:
```text
Raw HTML Sources
   ↓
Extraction to JSON
   ↓
Disease Chunks
   ↓
Processed Disease Documents
   ↓
Embedding
   ↓
ChromaDB
   ↓
Retrieval
```
Each stage incrementally transforms the raw HTML data, improving its structure and focus for semantic search, while preserving all clinical information integrity.

## 3. Raw Data
- **Source**: Medical knowledge bases and clinical reference sites covering skin conditions. Primarily from:
  - Atopic Dermatitis/Eczema (American Academy of Dermatology and clinical sources)
  - Psoriasis (dermatological educational materials)
  - Urticaria/Hives (medical reference databases)
- **Structure**: HTML-formatted clinical documentation with rich content hierarchies including overviews, symptoms, triggers, treatment, and self-care guidance.
- **Records Count**: 3 disease conditions with comprehensive multi-page documentation:
  - **Eczema/Atopic Dermatitis**: 7 HTML pages + structured JSON
  - **Psoriasis**: 7 HTML pages + structured JSON
  - **Urticaria/Hives**: 5 HTML pages + structured JSON
- **Example Schema** (after JSON conversion):
  - `condition_id`: "eczema_atopic_dermatitis"
  - `condition`: "Atopic Dermatitis"
  - `section`: "Overview" | "Symptoms" | "Treatment" | etc.
  - `subsection`: Optional subsection within the main section
  - `chunk_type`: "object" (for semantic units)
  - `content`: Structured dictionary with specific clinical fields
  - `text`: Human-readable formatted version of content
  - `source`: Reference metadata (title, URL, aliases)

## 4. Extraction & Parsing
The extraction stage (`src/data_ingestion/diseases_ingestion/chunk_*.py` files) parses raw HTML and structured data to produce disease-specific JSON chunks:
- **HTML Parsing**: Raw HTML pages are parsed using BeautifulSoup to extract meaningful sections.
- **Section Identification**: Content is organized by clinical sections (Overview, Symptoms, Causes, Treatment, Self-Care, etc.).
- **Semantic Segmentation**: Large sections are subdivided into logical, retrievable chunks maintaining context boundaries.
- **Text Normalization**: HTML entities are decoded, whitespace is normalized, and formatting is standardized for consistent retrieval.
- **Metadata Extraction**: Source URLs, page titles, and clinical aliases are preserved for provenance and filtering.

### Processing Files:
- `src/data_ingestion/diseases_ingestion/chunk_eczema.py` - Processes Atopic Dermatitis/Eczema documentation
- `src/data_ingestion/diseases_ingestion/chunk_psoriasis.py` - Processes Psoriasis documentation
- `src/data_ingestion/diseases_ingestion/chunk_urticaria.py` - Processes Urticaria/Hives documentation

## 5. Disease Chunks
The chunking stage produces three JSON files in `data/Chunked_Data/diseases_chunked/`:
- **eczema_atopic_dermatitis_chunked.json**: 59 semantic chunks covering Eczema/Atopic Dermatitis
- **psoriasis_chunked.json**: 57 semantic chunks covering Psoriasis
- **urticaria_hives_chunked.json**: 50 semantic chunks covering Urticaria/Hives

### Chunk Structure:
Each chunk maintains a consistent structure designed for semantic retrieval:
```json
{
  "chunk_id": "unique_identifier_per_chunk",
  "condition_id": "disease_identifier",
  "condition": "Display name of condition",
  "section": "Major section heading",
  "subsection": "Optional subsection",
  "chunk_type": "object",
  "source": {
    "name_en": "Condition name",
    "aliases": ["Alternative names"],
    "page_title": "Source page title"
  },
  "source_url": "https://original-source-url",
  "content": {
    "structured_fields": "vary by section type"
  },
  "text": "Human-readable formatted text for embedding"
}
```

## 6. Chunking Strategy
The current chunking strategy is: **One semantic unit per retrieval chunk, maintaining clinical context boundaries.**
- **Clinical Integrity**: Chunks respect semantic boundaries (e.g., all symptoms in one section stay together) to preserve the clinical meaning needed for accurate retrieval.
- **Context Preservation**: Avoiding mid-sentence splits ensures queries like "What are symptoms of eczema?" retrieve complete, coherent symptom lists rather than fragments.
- **Natural Object Boundaries**: Each disease section is treated as a logical retrieval unit. While individual pages could be split further, the current granularity (59-57-50 chunks across three diseases) balances retrieval precision against context loss.
- **Rationale**: Disease conditions require holistic understanding. Fragmenting symptom descriptions or treatment protocols would degrade retrieval quality for clinical decision support.

## 7. Processed Disease Documents
The processed documents exist as chunked JSON records optimized for retrieval:
- **Atomic Unit**: Each chunk represents a complete, semantically meaningful clinical unit.
- **`text` Field**: Formatted, human-readable string containing the complete clinical substance designed for dense retrieval (Condition, Section, Clinical Content, Source).
- **`metadata` Fields**: Structured fields for post-retrieval filtering and identification (`chunk_id`, `condition_id`, `condition`, `section`, `subsection`, `chunk_type`, `source_url`).
- **Total Processed Chunks**: 166 disease chunks across three conditions

## 8. Token Statistics
Token counts were analyzed using the `all-MiniLM-L6-v2` tokenizer on the 166 processed disease chunks. The distribution of tokens per chunk is as follows:
- **Total Processed Chunks**: 166
- **Total Token Count**: 28,847
- **Average Token Count**: 173.77
- **Median Token Count**: 168.0
- **Minimum Token Count**: 42
- **Maximum Token Count**: 389
- **P75**: 208.0
- **P90**: 254.0
- **P95**: 287.0
- **P99**: 356.0

### Per-Disease Token Statistics:
| Disease | Chunks | Total Tokens | Avg Tokens | Median | Max |
| ------- | ------ | ------------ | ---------- | ------ | --- |
| Eczema/Atopic Dermatitis | 59 | 10,352 | 175.46 | 171 | 354 |
| Psoriasis | 57 | 9,828 | 172.42 | 167 | 389 |
| Urticaria/Hives | 50 | 8,667 | 173.34 | 163 | 378 |

## 9. Embedding
The processed disease chunks are embedded into dense vectors using the following configuration (as verified from `embedding_manifest.json`):
- **Embedding Model**: `all-MiniLM-L6-v2`
- **Embedding Dimensions**: 384
- **Distance Metric**: cosine
- **Normalization**: true (normalized embeddings)
- **Total Embedded Chunks**: 166
- **Collection Name**: "diseases"
- **Processing Time**: 95.1 seconds
- **Batch Size**: 16 chunks
- **Processing Rate**: ~1.75 chunks/second

### Model Rationale:
The `all-MiniLM-L6-v2` model was selected over larger models (e.g., `BAAI/bge-m3`) because:
1. **Efficiency**: 384-dimensional embeddings vs. 1024-dim, reducing storage and search latency
2. **Disk Space**: ~90MB model size vs. 2.3GB for BGE-M3, critical for resource-constrained environments
3. **Performance**: Excellent performance on semantic similarity tasks despite smaller size
4. **Adequacy**: For disease retrieval with 166 chunks, the model's quality-to-efficiency trade-off is optimal

## 10. ChromaDB
The vector index is built in ChromaDB and located at `data/vectorstores/diseases_chroma/`. The internal structure includes:
- **`embedding_manifest.json`**: Describes the embedding model configuration and pipeline metadata.
- **`chroma.sqlite3`**: The SQLite database storing chunk metadata and relational tracking for Chroma.
- **`<uuid>` folder**: Contains the internal binary structures for the HNSW index:
  - `data_level0.bin`: Stores the raw dense vectors (166 × 384-dim vectors).
  - `header.bin`: HNSW graph header properties.
  - `link_lists.bin`: Edge connectivity structure for the HNSW graph.
  - `length.bin`: Contains vector length information.
*(Note: Exact internal binary layouts are proprietary to ChromaDB's hnswlib implementation, but their presence verifies a successfully built vector index).*

## 11. End-to-End Pipeline Summary

| Stage | Input | Output | Purpose |
| ----- | ----- | ------ | ------- |
| **Extraction** | Multiple HTML sources | Per-disease JSON files (raw) | Parse clinical content from HTML |
| **Chunking** | Raw disease JSON | `*_chunked.json` (166 total) | Segment into retrievable semantic units |
| **Processing** | Chunked JSON | Embedding-ready chunks | Format for semantic retrieval |
| **Embedding** | Disease chunks (166) | Dense vectors (384-dim) | Generate semantic representations via MiniLM-L6-v2 |
| **Storage** | Dense vectors & Metadata | ChromaDB (`diseases_chroma`) | Persist vectors and metadata for fast RAG retrieval |

## 12. Important Data Integrity Notes
During construction, the following aspects were observed:
- **Source Heterogeneity**: Disease chunks come from multiple authoritative clinical sources (American Academy of Dermatology, medical education databases). Source URLs and citations are preserved for all chunks.
- **Section Completeness**: Most chunks contain complete clinical information for their section. Empty sections are omitted rather than stored, preventing null/empty retrievals.
- **Clinical Consistency**: Terminology is standardized across chunks (e.g., consistent use of "flare", "exacerbation", "remission" for appropriate disease contexts).
- **Formatting Preservation**: Clinical formatting (e.g., key symptoms listed, treatment protocols) is maintained through the chunking pipeline to support structured and unstructured retrieval patterns.
- **Metadata Reliability**: All chunks include `source_url` and `source.name_en` for provenance tracking and citation verification.

---

## Retrieval Evaluation Strategy

To properly evaluate the disease chunk retrieval component, testing should cover various aspects of semantic search and clinical accuracy. The evaluation dataset should be constructed around the following question categories:

### Type A — Disease overview queries
- **Example**: "What is atopic dermatitis? What are its key characteristics?"
- **Expected Behavior**: Retrieve the Overview chunk for Atopic Dermatitis with comprehensive definition, chronicity, and epidemiology.

### Type B — Symptom identification queries
- **Example**: "What are the symptoms of psoriasis?"
- **Expected Behavior**: Retrieve Symptoms section(s) for Psoriasis with complete, clinically accurate symptom descriptions.

### Type C — Cause and trigger queries
- **Example**: "What triggers eczema flare-ups?"
- **Expected Behavior**: Retrieve Triggers and Causes sections that explain both internal and external factors driving disease exacerbation.

### Type D — Treatment and management queries
- **Example**: "What are the treatment options for urticaria?"
- **Expected Behavior**: Retrieve Treatment sections describing pharmacological and non-pharmacological interventions with proper clinical detail.

### Type E — Self-care and prevention queries
- **Example**: "How can someone manage eczema at home?"
- **Expected Behavior**: Retrieve Self-Care or Management sections with practical, evidence-based recommendations.

### Type F — Differential diagnosis support
- **Example**: "What is the difference between eczema and psoriasis?"
- **Expected Behavior**: Retrieve distinguishing characteristics from both diseases' Overview and Symptoms sections to support clinical differentiation.

### Type G — Condition severity and chronicity queries
- **Example**: "Is eczema a chronic condition? How long does it last?"
- **Expected Behavior**: Retrieve Overview sections clearly stating disease chronicity and natural history (remission, resolution rates in children, etc.).

### Type H — Age-specific queries
- **Example**: "What is infantile eczema? When do children usually develop atopic dermatitis?"
- **Expected Behavior**: Retrieve Overview and age-specific content clarifying disease onset and pediatric presentation.

### Type I — Comorbidity and complication queries
- **Example**: "Can eczema lead to infections? What are complications?"
- **Expected Behavior**: Retrieve comprehensive sections on disease complications and secondary infection risks.

### Type J — Epidemiology and commonality queries
- **Example**: "How common is psoriasis?"
- **Expected Behavior**: Retrieve epidemiological information from Overview sections describing prevalence and demographic distribution.

### Evaluation Example Distinctions
When designing answer expectations for evaluation, several important clinical distinctions must be maintained:
1. **Condition Present**: Chunk exists in database and fully addresses the query.
2. **Information Incomplete**: Chunk exists but the specific aspect is not covered (e.g., treatment query when only Overview is retrieved).
3. **Not Applicable**: Query addresses an aspect not present in the current disease database (e.g., drug interaction for a purely symptom-focused query).
4. **Retrieval Precision**: Distinguish between retrieving the correct disease's chunk vs. a semantically similar but clinically distinct disease chunk (e.g., psoriasis vs. eczema).

---

## Collection Scope and Limitations
- **Conditions Covered**: Atopic Dermatitis (Eczema), Psoriasis, Urticaria (Hives)
- **Chunk Count**: 166 semantic disease chunks
- **Embedding Dimension**: 384 (optimized for efficiency and retrieval speed)
- **Language**: English
- **Clinical Focus**: Dermatological conditions with emphasis on patient education and clinical decision support
- **Update Frequency**: As determined by project schedule and clinical content updates
