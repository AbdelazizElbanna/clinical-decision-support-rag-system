# Clinical Decision Support RAG System: Data Pipeline Documentation

This document provides a technical description of the data ingestion, cleaning, processing, chunking, embedding, and vector storage pipelines as implemented in this repository.

---

## 1. Overview & Data Scope

The repository hosts a dual-domain Retrieval-Augmented Generation (RAG) data pipeline designed for clinical decision support in dermatology and pharmacology. The system ingests raw clinical and pharmacological datasets, cleans and normalizes the content, applies domain-specific chunking strategies, generates dense vector representations, and persists them into separate ChromaDB collections.

### Data Domains

1. **Diseases Domain (Dermatology)**
   - **Covered Conditions**: Atopic Dermatitis (Eczema), Psoriasis, Urticaria (Hives).
   - **Source Data**: Scraped HTML medical documentation (primarily from the American Academy of Dermatology - AAD).
   - **Scale**: 3 disease conditions comprising multi-page HTML documentation parsed into structured JSON records and segmented into **166 semantic chunks**.

2. **Drugs Domain (Pharmacology)**
   - **Source Data**: Merged Egyptian drug databases compiled from upstream repositories (`mahmoudfalous/eg-drugs` and `karem505/egyptian-drug-database`).
   - **Scale**: 29,827 raw drug records cleaned and filtered to **5,978 skin and allergy domain drug records**.

---

## 2. API & Source Data Ingestion

| Data Domain | Raw Source Location | Format | Acquisition / Extraction Method | Output Location |
| :--- | :--- | :--- | :--- | :--- |
| **Diseases (Raw HTML)** | `data/raw/diseases/{Condition}/` | `.html` | Web scraping script (`src/scrap_diseases/testhtml.py`) using HTTP GET with custom User-Agent headers to pull AAD clinical pages. | `data/raw/diseases/` |
| **Drugs (Upstream 1)** | `data/raw/Drugs/eg-drugs-main/data/eg_drugs.json` | `.json` | Upstream dataset from `mahmoudfalous/eg-drugs` containing FDA warnings, Arabic usage summaries, barcodes, and pregnancy/organ warnings. | Merged into `unified_egyptian_drugs.json` |
| **Drugs (Upstream 2)** | `data/raw/Drugs/egyptian-drug-database-main/data/egyptian-drugs.json` | `.json` | Upstream dataset from `karem505/egyptian-drug-database` containing drug classes, administration routes, manufacturers, and active ingredients. | Merged into `unified_egyptian_drugs.json` |
| **Drugs (Merged Raw)** | `data/raw/Drugs/` | `.json`, `.csv` | Executed via `src/data_ingestion/drugs_ingestion/merge_drugs.py`, consolidating both sources by canonical drug key and active ingredients. | `data/raw/Drugs/unified_egyptian_drugs.json` (29,827 records) |
| **External Reference** | `data/raw/Openmeto/cities.json` | `.json` | Open-Meteo city coordinate records. | `data/raw/Openmeto/cities.json` |

---

## 3. Data Cleaning Pipeline

The cleaning stage normalizes raw input data and strips non-clinical noise without mutating core medical facts.

```text
Input File → Cleaning Script / Transformation → Cleaned Output File
```

### 3.1 Disease Data Cleaning (`convert_diseases_html_to_json.py`)

- **Script**: `src/data_ingestion/diseases_ingestion/convert_diseases_html_to_json.py`
- **Input**: Raw HTML files in `data/raw/diseases/`
- **Transformations**:
  1. **HTML Parsing & Noise Removal**: Uses BeautifulSoup (`lxml` parser) to decompose non-content tags (`script`, `style`, `noscript`, `iframe`, `svg`, `form`, `nav`).
  2. **Region Filtering**: Filters out elements matching CSS classes / IDs associated with web chrome (`header-public`, `footer`, `ad-container`, `breadcrumbs-bar-container`, `cookie-consent`, `soc-med-share-block`).
  3. **Text Normalization**: Collapses runs of whitespace (`\r`, `\n`, `\t`, multiple spaces) into single spaces. Removes stray leading colons and dash artifacts from HTML extraction (`clean_text()`).
  4. **Block Structure Extraction**: Extracts hierarchical headings (`h1`–`h6`), list items (`ul`, `ol`), paragraphs (`p`, `div`), and clinical image alt text (`[Image: ...]`) into an ordered block sequence.
  5. **Metadata Preservation**: Captures source page `<title>`, `og:url` / `<link rel="canonical">`, meta description, and ISO UTC extraction timestamp.
  6. **UI Filter**: Strips non-medical navigation noise (e.g., "advertisement", "sign in", "go", "search").
- **Output**: Cleaned HTML files and per-disease structured JSON files in `data/cleaned/diseases/` (e.g., `data/cleaned/diseases/Eczema Atopic Dermatitis/json/eczema_atopic_dermatitis.json`).

### 3.2 Drug Data Cleaning (`clean_drugs.py`)

- **Script**: `src/data_ingestion/drugs_ingestion/clean_drugs.py`
- **Input**: `data/raw/Drugs/unified_egyptian_drugs.json` (29,827 records)
- **Transformations**:
  1. **Arabic Field Removal**: Drops `name_ar`, `uses_ar`, and `warnings_summary_ar` to focus downstream retrieval on English clinical queries.
  2. **Text Normalization**: Strips surrounding whitespace, collapses internal whitespace runs, normalizes `||` separators, and collapses duplicate punctuation (`..`, `,,`). Capitalizes only the first character to preserve uppercase trade names and unit abbreviations (`clean_text()`).
  3. **Active Ingredient Normalization**: Standardizes spacing around `+` delimiters (`" + "`) and converts active ingredient strings to UPPERCASE (`normalize_ingredients()`).
  4. **Safety Warnings Transformation**: Maps boolean/null safety flags into standardized strings:
     - `True` → `"Caution required"`
     - `False` → `"No specific warning recorded"`
     - `null` / `None` → `"Insufficient information available; consult a doctor or pharmacist."`
     - If the entire `safety_warnings` object is null → `"Safety warning information unavailable; consult a doctor or pharmacist."`
  5. **Warning Summary Generation**: If `warnings_summary_en` is missing, constructs a summary listing active caution conditions (e.g., "Caution or warning advised under medical supervision for: Pregnancy, Kidney Disease.").
- **Output**: `data/cleaned/Drugs/cleaned_drugs.json` (29,827 records)

### 3.3 Drug Domain Filtering (`filter_skin_allergy_drugs.py`)

- **Script**: `src/data_ingestion/drugs_ingestion/filter_skin_allergy_drugs.py`
- **Input**: `data/cleaned/Drugs/cleaned_drugs.json` (29,827 records)
- **Transformations**:
  - Matches drug records against dermatological and allergic condition keyword lists:
    - **`DRUG_CLASS_KEYWORDS`**: Antihistamines, corticosteroids, immunosuppressants, emollients, moisturisers, topicals, antifungals, wound care, sunscreens, anti-acne.
    - **`ACTIVE_INGREDIENT_KEYWORDS`**: Cetirizine, loratadine, hydrocortisone, betamethasone, clobetasol, tacrolimus, dupilumab, acitretin, calcipotriol, urea, glycerol, etc.
    - **Condition Keywords**: Uses containing "eczema", "psoriasis", "urticaria", "atopic dermatitis", "dermatitis", "pruritus", "skin rash", "hives".
  - Retains **5,978 matching records** (~20% of full database) and removes 23,849 non-dermatological records (pure cardiovascular, diabetic, or neurological medications).
- **Output**: `data/cleaned/Drugs/filtered_skin_drugs.json` (5,978 records)

---

## 4. Processing Pipeline

The processing stage formats cleaned JSON records into retrieval-ready text representations and structured metadata dictionaries prior to chunking and embedding.

### 4.1 Disease Processing

- **Scripts**:
  - `src/data_ingestion/diseases_ingestion/chunk_eczema.py`
  - `src/data_ingestion/diseases_ingestion/chunk_psoriasis.py`
  - `src/data_ingestion/diseases_ingestion/chunk_urticaria.py`
- **Process**:
  - Iterates over top-level JSON sections (Overview, Symptoms, Causes, Risk Factors, Triggers, Environmental Factors, Skin Care, Flare-Up Management, Red Flags, When to See Doctor, Related Conditions, Medications and Treatments).
  - Recursively serializes section content into natural language key-value strings.
  - Prepends a standard header to every text block:
    ```text
    Condition: <Condition Name>
    Section: <Section Name>
    Subsection: <Subsection Name (if present)>
    ```
  - Appends source attribution text (`Source: American Academy of Dermatology (AAD)`, `Source URL: <URL>`).
  - Assembles structured metadata fields (`chunk_id`, `condition_id`, `condition`, `section`, `subsection`, `chunk_type`, `source`, `source_url`).
- **Output**: Saved in `data/Chunked_Data/diseases_chunked/`:
  - `eczema_atopic_dermatitis_chunked.json` (59 chunks)
  - `psoriasis_chunked.json` (57 chunks)
  - `urticaria_hives_chunked.json` (50 chunks)
  - **Total**: 166 processed disease chunks.

### 4.2 Drug Processing (`chunk_drugs.py`)

- **Script**: `src/data_ingestion/drugs_ingestion/chunk_drugs.py`
- **Input**: `data/cleaned/Drugs/filtered_skin_drugs.json` (5,978 records)
- **Process**:
  - **Text Construction (`build_page_content`)**: Builds a formatted multi-line text representation for dense vector encoding. Omits empty/null fields:
    ```text
    Drug Name: <Name>

    Active Ingredients: <Title-Cased Ingredients>

    Drug Class: <Title-Cased Class>

    Route: <Title-Cased Route>

    Manufacturer: <Title-Cased Manufacturer>

    Uses: <English Usage Text>

    Safety Warnings:
      Pregnancy: <Status>
      Lactation: <Status>
      ...

    Warning Summary: <Summary Text>
    ```
  - **Metadata Construction (`build_metadata`)**: Builds structured metadata for post-retrieval filtering and provenance:
    - `drug_id`, `slug`, `name_en`, `active_ingredients`, `drug_class`, `route`, `manufacturer`, `barcode`, `sources`, `safety_info_available` (boolean).
  - **LangChain Document Construction**: Wraps `page_content` and `metadata` into a LangChain `Document` object with `id = slug`.
- **Output**: `data/Chunked_Data/drugs_chunked/drugs_chunked.json` (5,978 processed document records).

---

## 5. Chunking Strategy

| Property | Disease Data Strategy | Drug Data Strategy |
| :--- | :--- | :--- |
| **Strategy Name** | Schema-Aware / Semantic Unit Chunking | Object-Level Contextual Chunking ("One Drug = One Document") |
| **Atomic Chunk Unit** | Single clinical section / subsection item | Complete individual drug record |
| **Data Chunked** | Structured section blocks (Symptoms, Triggers, Treatments) | Filtered drug JSON records (`filtered_skin_drugs.json`) |
| **Data Not Chunked** | Non-medical web UI elements, navigation headers, footers | Individual fields within a drug record (uses/warnings are not separated) |
| **Chunk Boundaries** | Logical JSON section and subsection boundaries | JSON object boundaries |
| **Explicit Chunk Size** | None (variable length determined by clinical section size) | None (variable length determined by drug record size) |
| **Overlap** | 0 tokens / 0 characters | 0 tokens / 0 characters |
| **Total Chunks** | **166 chunks** (59 Eczema + 57 Psoriasis + 50 Urticaria) | **5,978 document chunks** |
| **Rationale** | Preserves complete clinical topics (e.g., full symptom lists or trigger descriptions) without mid-sentence or mid-list splitting. | Prevents loss of clinical context. Splitting a drug's safety warnings or active ingredients from its trade name or dosage form would degrade retrieval accuracy for safety queries. |

---

## 6. Vector Embeddings & Storage Architecture

### 6.1 Embedding Models

| Domain | Embedding Model | Vector Dimension | Distance Metric | Normalization | Embedding Script |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Diseases** | `all-MiniLM-L6-v2` | 384 | Cosine | L2-normalized (`normalize_embeddings=True`) | `src/embeddings/embed_diseases/embed_diseases.py` |
| **Drugs** | `BAAI/bge-m3` | 1024 | Cosine | L2-normalized (`normalize_embeddings=True`) | `src/embeddings/embed_drugs/embed_drugs.py` |

### 6.2 Vector Store Architecture (ChromaDB)

Vector storage is strictly separated into two distinct ChromaDB collections to accommodate the different embedding models, vector dimensions, and domain entities.

```text
data/vectorstores/
├── diseases_chroma/
│   ├── chroma.sqlite3
│   ├── embedding_manifest.json
│   └── 38093330-995a-4d21-9697-da3f71589684/
│       ├── data_level0.bin
│       ├── header.bin
│       ├── length.bin
│       └── link_lists.bin
└── drugs_chroma/
    ├── chroma.sqlite3
    ├── embedding_manifest.json
    └── 05bbdd0e-dcae-4bb3-ba88-e67c13dcfdee/
        ├── data_level0.bin
        ├── header.bin
        ├── index_metadata.pickle
        ├── length.bin
        └── link_lists.bin
```

#### Collection 1: Disease Chroma Store
- **Directory**: `data/vectorstores/diseases_chroma/`
- **Collection Name**: `"diseases"`
- **Vector Count**: 166 dense vectors (384 dimensions)
- **Stored Metadata**: `condition_id`, `condition`, `section`, `subsection`, `chunk_type`, `source_url`, `source`, `content`
- **Manifest**: `data/vectorstores/diseases_chroma/embedding_manifest.json`

#### Collection 2: Drug Chroma Store
- **Directory**: `data/vectorstores/drugs_chroma/`
- **Collection Name**: `"drugs"`
- **Vector Count**: 5,978 dense vectors (1024 dimensions)
- **Stored Metadata**: `drug_id`, `slug`, `name_en`, `active_ingredients`, `drug_class`, `route`, `manufacturer`, `barcode`, `sources`, `safety_info_available`
- **Manifest**: `data/vectorstores/drugs_chroma/embedding_manifest.json`

---

## 7. Token Analysis

Token count analysis is executed via `src/embeddings/analyze_tokens.py` to inspect the distribution of token lengths across chunks and ensure no context truncation occurs against embedding model limits.

### 7.1 Disease Token Analysis (`Reports/Diseases/token_statistics.json`)
- **Tokenizer**: `sentence-transformers/all-MiniLM-L6-v2` (Max Context: 512 tokens)
- **Dataset Analyzed**: 166 processed disease chunks
- **Results**:
  - **Total Tokens**: 28,847
  - **Mean Tokens / Chunk**: 173.77
  - **Median Tokens**: 168.0
  - **Min Tokens**: 42
  - **Max Tokens**: 389
  - **P75**: 208.0 | **P90**: 254.0 | **P95**: 287.0 | **P99**: 356.0
- **Per-Disease Breakdown**:
  - *Eczema / Atopic Dermatitis* (59 chunks): 10,352 tokens (Mean: 175.46, Max: 354)
  - *Psoriasis* (57 chunks): 9,828 tokens (Mean: 172.42, Max: 389)
  - *Urticaria / Hives* (50 chunks): 8,667 tokens (Mean: 173.34, Max: 378)
- **Finding**: All 166 chunks fall well within the 512-token context limit of `all-MiniLM-L6-v2`.

### 7.2 Drug Token Analysis (`Reports/Drugs/token_statistics.json`)
- **Tokenizer**: `BAAI/bge-m3` (Max Context: 8,192 tokens)
- **Dataset Analyzed**: 5,978 processed drug documents
- **Results**:
  - **Total Tokens**: 1,004,988
  - **Mean Tokens / Document**: 168.11
  - **Median Tokens**: 162.0
  - **Min Tokens**: 28
  - **Max Tokens**: 521
  - **P75**: 202.0 | **P90**: 248.0 | **P95**: 272.0 | **P99**: 338.0
- **Finding**: All 5,978 documents fall well within the 8,192-token context limit of `BAAI/bge-m3`.

---

## 8. Samples & Intermediate Pipeline Data

The repository contains representative sample files under `Reports/Diseases/` and `Reports/Drugs/` documenting each intermediate data state:

### Diseases Lineage Samples (`Reports/Diseases/`)
- `raw_sample.json`: Representative raw converted HTML block object.
- `processed_sample.json`: Intermediate structured disease section object.
- `chunked_sample.json`: Final chunked disease object with `chunk_id`, `text`, and metadata.

### Drugs Lineage Samples (`Reports/Drugs/`)
- `raw_sample.json`: Original raw drug JSON object from merged upstream source.
- `cleaned_sample.json`: Output after running `clean_drugs.py` (Arabic removed, text normalized, safety warnings converted to text).
- `filtered_sample.json`: Output after running `filter_skin_allergy_drugs.py` (dermatology domain record).
- `chunked_sample.json`: Final document format with `id`, `page_content`, and `metadata`.

---

## 9. Evaluation Considerations

### 9.1 Currently Implemented Inspections
- **Token Distribution Analysis**: `src/embeddings/analyze_tokens.py` verifying context length compliance.
- **Structural Integrity Validation**: Pre-embedding sanity checks (`validate_disease_chunks()` and `validate_documents()`) checking for missing fields, empty strings, and duplicate IDs.
- **Embedding Reproducibility Tracking**: Generation of `embedding_manifest.json` recording parameters, model weights, dimension, timestamp, and vector counts.

### 9.2 Possible Future Evaluations (Not Implemented)
- **Retrieval Precision & Recall (Hit@k, MRR)**: Quantitative retrieval benchmarking across clinical question types.
- **Negative Query Abstention**: Evaluating system behavior when queried about non-dermatological drugs filtered out of the knowledge base.
- **Cross-Space Retrieval Quality**: Measuring the impact of separated vector spaces vs. unified cross-domain retrieval.

---

## 10. Repository Directory Structure

```text
clinical-decision-support-rag-system/
├── data/
│   ├── raw/
│   │   ├── diseases/                      # Raw HTML files grouped by condition
│   │   │   ├── Eczema Atopic Dermatitis/
│   │   │   ├── Psoriasis/
│   │   │   └── Urticaria_hives/
│   │   ├── Drugs/                         # Raw drug datasets & upstream sources
│   │   │   ├── eg-drugs-main/
│   │   │   ├── egyptian-drug-database-main/
│   │   │   ├── unified_egyptian_drugs.json
│   │   │   └── unified_egyptian_drugs.csv
│   │   └── Openmeto/                      # External geographical reference data
│   │       └── cities.json
│   ├── cleaned/
│   │   ├── diseases/                      # Converted HTML & per-disease JSON
│   │   └── Drugs/
│   │       ├── cleaned_drugs.json         # 29,827 cleaned drug records
│   │       └── filtered_skin_drugs.json   # 5,978 dermatology filtered records
│   ├── Chunked_Data/
│   │   ├── diseases_chunked/              # 166 chunked disease JSON files
│   │   │   ├── eczema_atopic_dermatitis_chunked.json
│   │   │   ├── psoriasis_chunked.json
│   │   │   └── urticaria_hives_chunked.json
│   │   └── drugs_chunked/                 # 5,978 chunked drug document records
│   │       └── drugs_chunked.json
│   └── vectorstores/
│       ├── diseases_chroma/               # Chroma collection 'diseases' (MiniLM-L6-v2, 384d)
│       └── drugs_chroma/                  # Chroma collection 'drugs' (BGE-M3, 1024d)
├── src/
│   ├── data_ingestion/
│   │   ├── diseases_ingestion/
│   │   │   ├── convert_diseases_html_to_json.py
│   │   │   ├── chunk_eczema.py
│   │   │   ├── chunk_psoriasis.py
│   │   │   └── chunk_urticaria.py
│   │   └── drugs_ingestion/
│   │       ├── merge_drugs.py
│   │       ├── clean_drugs.py
│   │       ├── filter_skin_allergy_drugs.py
│   │       └── chunk_drugs.py
│   ├── embeddings/
│   │   ├── analyze_tokens.py              # Token length distribution analyzer
│   │   ├── embed_diseases/
│   │   │   └── embed_diseases.py         # Disease vector store builder
│   │   └── embed_drugs/
│   │       └── embed_drugs.py            # Drug vector store builder
│   └── scrap_diseases/
│       └── testhtml.py                    # Web scraper test script
└── Reports/
    ├── Diseases/                          # Disease pipeline reports & sample artifacts
    │   ├── README_DISEASE_PIPELINE.md
    │   ├── token_statistics.json
    │   ├── raw_sample.json
    │   ├── processed_sample.json
    │   └── chunked_sample.json
    └── Drugs/                             # Drug pipeline reports & sample artifacts
        ├── README_DRUG_PIPELINE.md
        ├── token_statistics.json
        ├── raw_sample.json
        ├── cleaned_sample.json
        ├── filtered_sample.json
        └── chunked_sample.json
```

---

## 11. End-to-End Data Flow

```text
DISEASES PIPELINE                                DRUGS PIPELINE
================                                ==============

Raw HTML Pages (AAD Scraped)                    Upstream Datasets (eg-drugs, egyptian-drug-db)
       │                                                               │
       ▼                                                               ▼
src/scrap_diseases/testhtml.py                 src/data_ingestion/drugs_ingestion/merge_drugs.py
       │                                                               │
       ▼                                                               ▼
data/raw/diseases/*.html                        data/raw/Drugs/unified_egyptian_drugs.json (29,827)
       │                                                               │
       ▼                                                               ▼
convert_diseases_html_to_json.py               clean_drugs.py
(Strip HTML noise, extract blocks)              (Remove Arabic, normalize text/ingredients/safety)
       │                                                               │
       ▼                                                               ▼
data/cleaned/diseases/*/json/*.json            data/cleaned/Drugs/cleaned_drugs.json (29,827)
       │                                                               │
       ▼                                                               ▼
chunk_eczema.py / chunk_psoriasis.py / ...     filter_skin_allergy_drugs.py
(Section-level schema-aware chunking)          (Dermatology keyword domain filter)
       │                                                               │
       ▼                                                               ▼
data/Chunked_Data/diseases_chunked/*.json (166) data/cleaned/Drugs/filtered_skin_drugs.json (5,978)
       │                                                               │
       │                                                               ▼
       │                                       chunk_drugs.py
       │                                       (Object-level LangChain Document formatting)
       │                                                               │
       ▼                                                               ▼
embed_diseases.py                              data/Chunked_Data/drugs_chunked/drugs_chunked.json
(Model: all-MiniLM-L6-v2, 384-dim)                                     │
       │                                                               ▼
       ▼                                       embed_drugs.py
data/vectorstores/diseases_chroma/             (Model: BAAI/bge-m3, 1024-dim)
(Collection: "diseases", 166 vectors)                                 │
                                                                       ▼
                                               data/vectorstores/drugs_chroma/
                                               (Collection: "drugs", 5,978 vectors)
```