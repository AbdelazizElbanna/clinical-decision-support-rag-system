# Drug RAG Data Pipeline

## 1. Overview
This document provides a complete technical description of the drug data pipeline for the clinical decision support RAG system. It documents the exact lifecycle of drug data from raw JSON extraction through cleaning, filtering, processing into LangChain Documents, and embedding into ChromaDB using the `BAAI/bge-m3` embedding model. It also establishes an evaluation strategy for the resulting knowledge base.

## 2. Dataset Lifecycle
The data processing pipeline follows these sequential stages:
```text
Raw Data
   ↓
Cleaning
   ↓
Filtered Drug Dataset
   ↓
Processed Drug Documents
   ↓
Embedding
   ↓
ChromaDB
   ↓
Retrieval
```
Each stage incrementally transforms the raw data, improving its structure and focus for semantic search, without mutating the core clinical information.

## 3. Raw Data
- **Source**: Unified Egyptian drug database (e.g., `unified_egyptian_drugs.json`). Sourced from multiple upstream datasets (e.g., `karem505/egyptian-drug-database`, `mahmoudfalous/eg-drugs`).
- **Structure**: A large JSON array of drug objects.
- **Records Count**: 29,827 total records.
- **Example Schema**:
  - `slug`: "1-2-3-one-two-three-20-f-c-tabs"
  - `name_en`: "1 2 3 (ONE TWO THREE) 20 F.C.TABS."
  - `name_ar`: "ون تو ثري 20 قرص"
  - `active_ingredients`: "CHLORPHENIRAMINE+PARACETAMOL(ACETAMINOPHEN)+PSEUDOEPHEDRINE"
  - `drug_class`: "COLD PRODUCTS"
  - `route`: "ORAL.SOLID"
  - `manufacturer`: "HIKMA PHARMA"
  - `uses_ar`: (Arabic usage description)
  - `uses_en`: (English usage description)
  - `safety_warnings`: {"pregnancy": true, "kidney": false, ...}
  - `warnings_summary_ar`: (Arabic warning summary)
  - `warnings_summary_en`: (English warning summary)
  - `barcode`: "6221000000010"
  - `sources`: Array of source references.

## 4. Cleaning
The cleaning stage (`src/data_ingestion/drugs_ingestion/clean_drugs.py`) applies the following operations to produce `cleaned_drugs.json`:
- **Arabic Removal**: Removed `name_ar`, `uses_ar`, and `warnings_summary_ar`.
- **Text Normalization**: Stripped whitespace, collapsed multiple spaces, and collapsed duplicate punctuations. Capitalized only the very first character of text fields (preserving acronyms/dosages).
- **Ingredient Normalization**: Active ingredients were converted to UPPERCASE, and `+` separators were normalized to have exactly one space on each side.
- **Safety Info Transformation**: `safety_warnings` booleans were translated into strings. `True` became "Caution required", `False` became "No specific warning recorded", and `null` became "Insufficient information available; consult a doctor or pharmacist."
- **Warning Summary Generation**: If `warnings_summary_en` was missing, it was dynamically constructed based on active cautions in `safety_warnings`.

## 5. Filtering
The filtering stage (`src/data_ingestion/drugs_ingestion/filter_skin_allergy_drugs.py`) targets skin and allergy domain drugs:
- **Criterion**: Records were retained if they matched specific keywords related to dermatology, eczema, psoriasis, or urticaria.
- **Implementation**: The script checks `drug_class`, `active_ingredients`, and `uses_en` for matches against lists like `DRUG_CLASS_KEYWORDS` (e.g., "antihistamine", "corticosteroid", "emollient") and `ACTIVE_INGREDIENT_KEYWORDS` (e.g., "cetirizine", "hydrocortisone", "tacrolimus", "dupilumab"). Uses containing "eczema", "psoriasis", etc. were also retained.
- **Records Retained**: 5,978 records (approx. 20% of the raw dataset).
- **Records Removed**: 23,849 records belonging to non-dermatological domains (e.g., pure cardiovascular, diabetic, or neurological medications with no skin relevance).

## 6. Processed Drug Documents
The chunking/processing stage (`src/data_ingestion/drugs_ingestion/chunk_drugs.py`) transforms the filtered dataset into retrieval-ready LangChain Documents (`drugs_documents.json`).
- **One Drug = One Retrieval Document**: The atomic unit is the full drug record.
- **`page_content`**: A formatted, human-readable string containing clinical substance designed for dense retrieval (Drug Name, Active Ingredients, Drug Class, Route, Manufacturer, Uses, Safety Warnings).
- **`metadata`**: Structured fields for post-retrieval filtering, identification, and provenance (`drug_id`, `slug`, `name_en`, `active_ingredients`, `drug_class`, `route`, `manufacturer`, `barcode`, `sources`, `safety_info_available`).

## 7. Chunking Strategy
The current chunking strategy is: **One drug record per retrieval document/chunk.**
- This strategy avoids the loss of context that recursive character splitting would cause. A user query ("Is drug X safe for pregnancy?") requires the full context of the drug to be answered accurately.
- Slicing a drug record mid-sentence or separating warnings from uses would severely degrade retrieval performance. Thus, the natural object boundary is maintained.

## 8. Token Statistics
Token counts were analyzed using the `BAAI/bge-m3` tokenizer on the 5,978 processed documents. The distribution of tokens per document is as follows:
- **Total Processed Documents**: 5,978
- **Total Token Count**: 1,004,988
- **Average Token Count**: 168.11
- **Median Token Count**: 162.0
- **Minimum Token Count**: 28
- **Maximum Token Count**: 521
- **P75**: 202.0
- **P90**: 248.0
- **P95**: 272.0
- **P99**: 338.0

## 9. Embedding
The processed documents are embedded into dense vectors using the following configuration (as verified from `embedding_manifest.json`):
- **Embedding Model**: `BAAI/bge-m3`
- **Embedding Dimensions**: 1024
- **Distance Metric**: cosine
- **Normalization**: true (normalized embeddings)
- **Total Embedded Documents**: 5,978
- **Collection Name**: "drugs"

## 10. ChromaDB
The vector index is built in ChromaDB and located at `data/vectorstores/drugs_chroma/`. The internal structure includes:
- **`embedding_manifest.json`**: Describes the embedding model configuration.
- **`chroma.sqlite3`**: The SQLite database storing document metadata and relational tracking for Chroma.
- **`<uuid>` folder (`05bbdd0e-dcae-4bb3-ba88-e67c13dcfdee`)**: Contains the internal binary structures for the HNSW index:
  - `data_level0.bin`: Stores the raw dense vectors.
  - `header.bin`: HNSW graph header properties.
  - `index_metadata.pickle`: Pickled metadata mapping for the index.
  - `length.bin`: Contains vector lengths/counts.
  - `link_lists.bin`: Edge connectivity structure for the HNSW graph.
*(Note: Exact internal binary layouts are proprietary to ChromaDB's hnswlib implementation, but their presence verifies a successfully built vector index).*

## 11. End-to-End Pipeline Summary

| Stage | Input | Output | Purpose |
| ----- | ----- | ------ | ------- |
| **Ingestion** | Multiple sources | `unified_egyptian_drugs.json` (29,827) | Consolidate raw drug dataset |
| **Cleaning** | `unified_egyptian_drugs.json` | `cleaned_drugs.json` (29,827) | Remove Arabic, normalize text, structure safety info |
| **Filtering** | `cleaned_drugs.json` | `filtered_skin_drugs.json` (5,978) | Retain only dermatology/allergy domain drugs |
| **Processing** | `filtered_skin_drugs.json` | `drugs_documents.json` (5,978) | Map JSON objects into LangChain Documents |
| **Embedding** | `drugs_documents.json` | Dense vectors (1024-dim) | Generate semantic representations via BGE-M3 |
| **Storage** | Dense vectors & Metadata | ChromaDB (`drugs_chroma`) | Persist vectors and metadata for fast RAG retrieval |

## 12. Important Data Integrity Notes
During inspection, the following aspects were observed:
- **Missing Information**: Not all records have comprehensive uses or active ingredients (e.g., missing or minimal English descriptions). The system handles this gracefully by omitting empty sections in `page_content`.
- **Safety Completeness**: Many drugs lack specific clinical trial warnings in the source data. The cleaning pipeline handles these instances explicitly with `"No specific warning recorded"` or `"Unavailable"`. It is crucial that the LLM does not hallucinate safety info if it sees these strings.
- **Formatting Variability**: Some ingredients still retain parenthetical structures and acronyms (e.g. `PARACETAMOL(ACETAMINOPHEN)`), but `clean_drugs.py` and `chunk_drugs.py` normalize spacing and casing sufficiently for the `bge-m3` subword tokenizer.

---

## Retrieval Evaluation Strategy

To properly evaluate the retrieval component, testing must cover various aspects of semantic and metadata-based searches. The evaluation dataset should be constructed around the following question categories:

### Type A — Existing drug exact-name queries
- **Example**: "What is the safety information for 1 2 3 (ONE TWO THREE) 20 F.C.TABS.?"
- **Expected Behavior**: Retrieve the exact drug record and return the safety information accurately.

### Type B — Existing drug partial-name queries
- **Example**: "Tell me about 1 2 3 syrup."
- **Expected Behavior**: Retrieve the specific formulation matching the partial query (if available) or relevant alternatives.

### Type C — Ingredient-based retrieval
- **Example**: "Which available drug contains pseudoephedrine?"
- **Expected Behavior**: Retrieve drugs whose active ingredients contain the specific queried ingredient.

### Type D — Drug-class retrieval
- **Example**: "Which available drugs belong to cold products?"
- **Expected Behavior**: Retrieve drug records belonging to that specific class.

### Type E — Safety-condition queries
- **Example**: "Which available drugs have warnings for hypertension?"
- **Expected Behavior**: Retrieve drugs whose safety warnings contain "Caution required" for hypertension.

### Type F — Route/formulation queries
- **Example**: "Which available drug is an oral solid containing paracetamol?"
- **Expected Behavior**: Accurately combine semantic queries about ingredients and structured properties (route).

### Type G — Negative retrieval (Crucial)
- **Example**: "What are the safety warnings for [Cardiovascular Drug Removed by Filter]?"
- **Expected Behavior**: The system must fail to retrieve the drug (since it's absent from the filtered dataset of 5,978 records) and state that the drug is unavailable in the system. The LLM must not hallucinate a generic response.

### Type H — Near-match / confusable drugs
- **Example**: Given products like "1 2 3", "1 2 3 EXTRA", "1 2 3 SYRUP", ask: "Does 1 2 3 SYRUP have the same ingredients as the tablets?"
- **Expected Behavior**: Retrieve the exact queried formulations without confusing them with similarly named variants.

### Type I — Ingredient overlap
- **Example**: "Compare products containing Paracetamol."
- **Expected Behavior**: Retrieve distinct product records sharing an ingredient without inappropriately collapsing them into one entity.

### Type J — Missing-information queries
- **Example**: Queries about a drug where safety information is marked as "Unavailable" or "No specific warning recorded".
- **Expected Behavior**: The system must accurately distinguish between "Information is unavailable in the dataset" and "The drug has no warning."

### Evaluation Example Distinctions
When designing answers for evaluation, three states must be strictly differentiated:
1. **Case 1 (No Warning)**: Drug exists; safety field is "No specific warning recorded". (Meaning: No specific warning was recorded in the dataset).
2. **Case 2 (Not Found)**: Drug was removed by the domain filter. (Meaning: The requested drug is not available in the current knowledge base).
3. **Case 3 (Unavailable Info)**: Drug exists, but the requested field is missing or states "Unavailable". (Meaning: That information is unavailable in the source dataset).
