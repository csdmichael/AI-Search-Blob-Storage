# Use Case: RF Filter Design — Filter Design AI Assistant

> **Clone this folder** if you want to build a Foundry Agent that provides actionable filter design recommendations to RF engineers using Azure AI Search.
>
> **Audience**: Microsoft Solution Engineers presenting to RF/semiconductor filter design teams
> **Duration**: ~30 minutes for full demo

---

## Architecture

![Architecture](architecture.png)

### Components

| Component | Resource | Description |
|-----------|----------|-------------|
| **Azure Blob Storage** | `aistoragemyaacoub` | Stores 100 `.pdf` + 100 `.json` documents in the `filter-design-docs` container |
| **JSON Sidecar Files** | `FD-TC-XXXX.json` beside each `.pdf` | Machine-readable structured metadata — eliminates lossy PDF extraction |
| **Azure AI Search** | `ai-search-my` | Indexes documents with semantic + keyword search; refreshes daily at 8 AM PST |
| **AI Foundry Agent** | `Filter-Design-Agent` | Provides design recommendations using only AI Search — no web search or fabrication |
| **Managed Identity** | `DefaultAzureCredential` | All authentication uses managed identity — no keys or secrets |
| **Private VNET** | Existing VNET | Blob Storage and AI Search accessed via private endpoints |
| **Ranking & Feedback** | `ranking_feedback.py` | Feedback-driven re-ranking to improve accuracy from 90% to 95% |

### Deployed Web App URLs

| App | URL | Description |
|-----|-----|-------------|
| **API** | https://ai-search-agent-api.azurewebsites.net | FastAPI backend — proxies chat, batch, feedback, and prompt endpoints |
| **UI** | https://ai-search-agent-ui.azurewebsites.net | Ionic Angular chat UI — Copilot-style interface with use-case tabs |

---

## What This Use Case Demonstrates

1. **Advanced AI Search** — section-level chunking, custom scoring profiles, metadata-enriched facets
2. **Feedback-Driven Re-Ranking** — collecting relevance feedback, computing boost maps, re-ranking search results
3. **Accuracy Improvement Pipeline** — from 50% baseline to 90%+ through JSON indexing, semantic search, and feedback

---

## Quick Start

### Prerequisites

- **Azure CLI** installed and logged in (`az login`)
- **Python 3.10+** installed
- Azure resources provisioned (Storage Account, AI Search, AI Foundry Project, deployed model)
- `pip install -r requirements.txt` completed

### Setup

```bash
# Set the use case
export USE_CASE=filter_design     # Linux/Mac
$env:USE_CASE = "filter_design"   # PowerShell

# Generate 100 RF filter design documents (.pdf + .json sidecars)
python scripts/generate_filter_docs.py

# Upload to Blob Storage (filter-design-docs container)
python scripts/upload_to_blob.py

# Create AI Search index and indexer
python scripts/create_search_index.py

# Create enhanced chunked index with scoring profile
python scripts/chunk_and_index.py

# Create Foundry agent (Filter-Design-Agent)
export AZURE_AI_SEARCH_CONNECTION_NAME="ai-search-my"
python scripts/create_agent.py

# Fine-tune and evaluate
python scripts/fine_tune_and_evaluate.py

# Run ranking & feedback evaluation
python scripts/ranking_feedback.py

# Test
python scripts/test_search.py

# Generate architecture diagram
python scripts/generate_architecture_diagram.py
```

### Key Scripts

| Script | Purpose |
|--------|---------|
| `scripts/generate_filter_docs.py` | Generate 100 RF filter design `.pdf` + `.json` files |
| `scripts/upload_to_blob.py` | Upload to `filter-design-docs` container |
| `scripts/create_search_index.py` | Create standard AI Search index + indexer |
| `scripts/chunk_and_index.py` | Section-level chunking with scoring profile |
| `scripts/create_agent.py` | Create `Filter-Design-Agent` in Foundry |
| `scripts/fine_tune_and_evaluate.py` | Fine-tune model + evaluate citation accuracy |
| `scripts/ranking_feedback.py` | Ranking & feedback loop evaluation |
| `scripts/test_search.py` | Run semantic + keyword search tests |

---

## Demo Script

### Act 1: The Problem (2 min)

**Talking Points:**
- RF filter design teams manage hundreds of design specs, simulation reports, and characterization data across SAW, BAW, FBAR, and TC-SAW technologies
- Designers spend 20+ minutes hunting for specific S-parameter data, acceptance criteria, or past corrective actions across PDF documents
- Existing search gives ~90% accuracy but the team needs **95%+** for production use — wrong filter specs can cost $500K+ in re-spins
- Goal: Build an AI assistant that provides **actionable design recommendations** with cited sources, improving from 90% → 95% accuracy using a feedback loop

### Act 2: PDF Document Generation & Upload (5 min)

**2.1 — Generate filter design documents**

```bash
export USE_CASE=filter_design
python scripts/generate_filter_docs.py
```

Open `data/filter-design-docs/FD-TC-0001.pdf` and walk through the structure:
- **Professional PDF format** with headers, section titles, and structured data
- **9 sections**: Objective, Scope, Design Parameters, Test Procedure, Acceptance Criteria, Test Results, Observations, Corrective Actions, Sign-off
- **Domain-specific data**: center frequency, bandwidth, insertion loss, Q factor, substrate material, electrode stack, package type

> **Key Point**: Real filter design documents follow this structure — the generated PDFs are realistic enough for meaningful search evaluation.

**2.2 — Upload to Blob Storage**

```bash
python scripts/upload_to_blob.py
```

> **Key Point**: PDFs go to a **separate container** (`filter-design-docs`) from manufacturing docs (`engineering-docs`). Each use case is completely isolated at the storage level. Private endpoint ensures data never leaves the VNET.

### Act 3: AI Search Best Practices — JSON Index & Chunking Deep Dive (10 min)

**3.1 — The accuracy problem with PDF extraction**

```bash
python scripts/create_search_index.py
```

- A filter design PDF is ~2-3 pages; text extraction via PyPDF is lossy and can drop or mangle numeric values
- Querying "What is the insertion loss for Band 7 SAW filters?" on raw PDFs returns the entire document with garbled numbers
- **This is why the original PDF-based approach gave only 50% agent citation accuracy**

**3.2 — Switch to JSON index (the accuracy fix)**

Each run creates BOTH a PDF and a JSON file per document:
```
FD-TC-0001.pdf  ← human-readable, kept for reference
FD-TC-0001.json ← machine-readable, used for indexing
```

The JSON structure:
```json
{
  "document_number": "FD-TC-0001",
  "filter_type": "SAW (Surface Acoustic Wave)",
  "frequency_band": "Band 7 (2600 MHz)",
  "insertion_loss_measured_db": 1.52,
  "return_loss_measured_db": 18.3,
  "rejection_measured_db": 42.1,
  "q_factor": 2500,
  "sections": { "6_TEST_RESULTS": "...", ... }
}
```

> **Key Point**: Every field is explicit and exact in JSON. No text extraction, no regex parsing, no chance of a number being misread from a PDF layout. This is the single biggest accuracy improvement.

**3.3 — Section-level chunking from JSON**

```bash
python scripts/chunk_and_index.py
```

`chunk_and_index.py` automatically detects JSON files and uses them in preference to PDFs:

```
FD-TC-0001.json → 10 chunks:
  Document Header      (~745 chars) ← ALL key metrics inline
  1. OBJECTIVE          (~300 chars)
  ...
  9. SIGN-OFF           (~150 chars)
```

> **Key Point**: A query like "What is the Q factor for FD-TC-0001?" retrieves just the Document Header chunk (745 chars) and returns the exact value instantly.

**3.4 — Custom scoring profile**

| Field | Weight | Why |
|-------|--------|-----|
| `title` | **3.0×** | Most descriptive field |
| `document_number` | **2.5×** | Exact doc lookup should rank #1 |
| `section_name` | **2.0×** | Boosts chunks from the queried section |
| `content` | **1.0×** | Baseline for everything else |

### Act 4: The Feedback Loop — 50% → 90%+ (10 min)

**4.1 — Why the original approach gave only 50%**

Two root causes:

1. **Wrong query type**: The agent was using `SIMPLE` (keyword) queries. Queries like *"Which BAW filters have insertion loss below 1.5 dB?"* require semantic understanding.

2. **Disconnected feedback loop**: `ranking_feedback.py` was targeting the `standard_index` while the agent queries the `chunked_index`. Feedback boosts were never applied to agent queries.

**4.2 — The fixes applied**

```python
# Fix 1: Semantic query type (create_agent.py)
DEFAULT_QUERY_TYPE = AzureAISearchQueryType.SEMANTIC

# Fix 2: Feedback loop targets correct index (ranking_feedback.py)
INDEX_NAME = _uc_search["chunked_index"]["name"]

# Fix 3: JSON-based index (chunk_and_index.py)
# Auto-detects .json files and uses them over PDFs
```

**4.3 — How feedback-driven re-ranking works**

```bash
python scripts/ranking_feedback.py
```

**Layer 1: JSON Index + Semantic Reranking (baseline — 90%)**
- JSON-structured documents ensure all fields are queryable without text extraction
- Azure AI Search's semantic ranker scores results by meaning, not keywords

**Layer 2: Feedback Boost Map (continuous improvement)**
```python
boost = 1.0 + (relevant_count - irrelevant_count) × 0.05  # Clamped to [0.8, 1.5]
final_score = base_semantic_score × boost
```

**Layer 3: Threshold Filtering**
- Results below relevance threshold (default 0.7) are dropped
- Agent gets 5 highly relevant chunks instead of 10 mixed-quality ones

**4.4 — The improvement flywheel**

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│ User queries │────▶│ Agent answers │────▶│ User rates     │
│ the agent    │     │ with citations│     │ relevant/not   │
└─────────────┘     └──────────────┘     └────────┬───────┘
       ▲                                          │
       │            ┌──────────────┐              │
       │            │ Feedback     │◀─────────────┘
       └────────────│ boosts       │
                    │ re-ranking   │
                    └──────────────┘
```

> **Key Point**: This is a **self-improving system**. Every time an engineer uses the agent and rates a result, the system gets smarter. No re-training required.

### Act 5: The Agent in Action (3 min)

**5.1 — Create the filter design agent**

```bash
python scripts/create_agent.py
```

- **Single tool**: Azure AI Search (no web search)
- **Strict instructions**: Never fabricate specifications — wrong numbers are dangerous in filter design
- **Always cite sources**: Every claim linked to a specific FD-TC document

**5.2 — Live queries**

```bash
python scripts/test_search.py
```

**5.3 — 10 Example Prompts with Expected Results**

| # | Prompt | Expected Result | What It Tests |
|---|--------|----------------|---------------|
| 1 | *"What is the measured insertion loss and return loss for FD-TC-0001?"* | Exact IL and RL values from Section 6 with citation `[FD-TC-0001.pdf†...]` | Specific document lookup |
| 2 | *"Which TC-SAW filters target Band 7 and what were their results?"* | Lists FD-TC docs with filter_type=TC-SAW and frequency_band=Band 7 | Faceted metadata query |
| 3 | *"What corrective actions are recommended in FD-TC-0005?"* | Quoted actions from Section 8 | Section-level grounding |
| 4 | *"What substrates are used for FBAR filter designs?"* | Lists substrate materials from FBAR documents with citations | Cross-document aggregation |
| 5 | *"Compare insertion loss across all filter designs that use LiNbO3 substrate."* | Table of IL values from LiNbO3-based designs, each cited | Comparative analysis |
| 6 | *"What is the Q factor for FD-TC-0010?"* | Exact Q factor value from Design Parameters section | Single-field extraction |
| 7 | *"Which filter designs have FAIL status and why?"* | Lists failed designs with failure reasons | Status-filtered reasoning |
| 8 | *"What design tools were used for 5G NR n78 band filters?"* | Lists tools from n78 band documents | Metadata + tool extraction |
| 9 | *"Show the acceptance criteria for duplexer isolation."* | Specific isolation thresholds from duplexer test cases | Criteria extraction |
| 10 | *"What package types are used for BAW filters and what are their die sizes?"* | Lists package types and die dimensions from BAW documents | Multi-field extraction |

**Demo tip**: For prompts 1, 3, and 6, open the actual PDF side-by-side to show the audience the agent's numbers match the source document exactly.

### Closing: What the Customer Gets

1. **50% → 90%+ accuracy pipeline** — JSON index eliminates PDF extraction failures; semantic search handles natural language; fixed feedback loop amplifies what works
2. **Domain-specific agent** — understands RF filter terminology, never makes up specifications
3. **10 search best practices** — production-grade JSON indexing, semantic search, scoring, and chunking
4. **Self-improving system** — gets better with every query, no re-training needed
5. **Easy to customize** — change `config/agent_config.json` to adapt instructions, scoring weights, and thresholds
6. **Separate from other use cases** — isolated containers, indexes, and agents; clone just this folder

---

## Sample Search Prompts

### Semantic Search

| # | Prompt | Expected Results |
|---|--------|-----------------|
| 1 | *"What filter designs target 5G NR sub-6 GHz bands?"* | SAW/BAW filters for n77/n78/n79 bands |
| 2 | *"Which filter test cases failed and what corrective actions exist?"* | Failed designs with recommended geometry/material changes |
| 3 | *"How does temperature affect SAW filter frequency stability?"* | TC-SAW and temperature coefficient documents |
| 4 | *"What are the acceptance criteria for BAW filter insertion loss?"* | BAW/FBAR filter acceptance criteria sections |
| 5 | *"Show me test results for WiFi 6E coexistence filters"* | WiFi 6E (6 GHz) filter test results |

### Keyword Search

| # | Prompt | Expected Results |
|---|--------|-----------------|
| 1 | *"SAW filter Band 7 insertion loss"* | Band 7 SAW filter documents |
| 2 | *"BAW FBAR 5G NR n77"* | BAW/FBAR 5G NR Band n77 designs |
| 3 | *"TC-SAW temperature compensation"* | TC-SAW temperature stability documents |
| 4 | *"duplexer isolation rejection"* | Duplexer module isolation specs |
| 5 | *"FD-TC-0015"* | Specific filter design document by number |

---

## AI Search Best Practices

### 1. JSON-First Indexing

Reads `FD-TC-XXXX.json` sidecar files when available — exact field values, no PDF parsing. Each JSON contains all structured metadata fields (`document_number`, `filter_type`, `frequency_band`, `substrate_material`, all S-parameters, Q factor, temperature coefficient) plus all document sections.

### 2. Section-Level Chunking

Each document is split into section-level chunks (Objective, Scope, Design Parameters, etc.) instead of full-document indexing. Each chunk retains a context prefix (`Document: FD-TC-XXXX | Title\nSection: ...`) for provenance.

### 3. Metadata-Enriched Fields

Every chunk includes structured filterable/facetable metadata:
```
document_number, title, status, filter_type, frequency_band,
substrate_material, section_name, source_file
```

### 4. Custom Scoring Profile

| Field | Weight | Rationale |
|-------|--------|-----------|
| `title` | 3.0× | Most descriptive of document content |
| `document_number` | 2.5× | Exact lookup by doc ID should rank highest |
| `section_name` | 2.0× | Users often search for specific sections |
| `content` | 1.0× | Baseline full-text search |

### 5. Semantic Configuration with Keywords

Includes `keywords_fields` for `document_number` and `section_name` to improve the semantic ranker.

### 6. Overlap for Large Sections

Sections exceeding 2000 chars are split with 200-char overlap at line boundaries.

### 7. English Microsoft Analyzer

All searchable fields use `en.microsoft` for lemmatization and technical vocabulary handling.

### 8. Idempotent Operations

All creation uses `create_or_update_*` methods — safe to re-run without cleanup.

### 9. Batch Upload with BufferedSender

`SearchIndexingBufferedSender` handles batching, retries, and throttling for 700+ chunks.

### 10. Daily Scheduled Refresh & Managed Identity

Indexer runs at 8:00 AM PST (16:00 UTC) daily. All connections use `DefaultAzureCredential` — no secrets in code.

---

## JSON Sidecar Files

Each `.pdf` document is generated alongside a companion **`FD-TC-XXXX.json` sidecar** containing every field as structured data (filter type, frequency band, substrate material, all S-parameters, Q factor, temperature coefficient, and all document sections). These JSON files are:

- **Uploaded to Blob Storage** alongside the `.pdf` files by `upload_to_blob.py`
- **Used by `chunk_and_index.py`** as the authoritative source for the AI Search chunked index, eliminating lossy PDF text extraction
- **The primary reason demo accuracy improved from ~50% to 100%** (10/10 demo queries) and fine-tune citation accuracy reached 100% (20 samples)

### Why JSON Sidecars?

| Without JSON (PDF extraction) | With JSON Sidecars |
|---|---|
| PDF text extraction is lossy and layout-dependent | All fields are exact — no parsing errors |
| Numbers can be mis-read or truncated | Numeric fields stored as typed values |
| Cross-document queries often fail | Filterable/facetable metadata fields enable precise queries |
| Agent accuracy: ~50% | Agent accuracy: **100%** (demo) / **90%+** (ranking) |

---

## Ranking & Feedback Loop

The project includes a ranking and feedback system to improve agent accuracy from 90% to 95%.

### How It Works

1. **Feedback Collection**: Each query-document pair is rated as relevant/irrelevant
2. **Boost Map**: Documents with positive feedback get boost factors (up to 1.5×) applied on top of semantic reranker scores
3. **Re-Ranking**: Results are re-sorted using `base_score × boost_factor`
4. **Threshold Filtering**: Results below the configured relevance threshold are suppressed
5. **Evaluation**: Measures both search ranking accuracy and agent citation accuracy

```bash
USE_CASE=filter_design python scripts/ranking_feedback.py
```

See [ranking_report.md](ranking_report.md) for the latest evaluation report.

---

## Fine-Tuning & Evaluation

Q&A pairs are auto-extracted from documents. The model is fine-tuned (or evaluated with the base model if fine-tuning is unavailable in the region).

```bash
USE_CASE=filter_design python scripts/fine_tune_and_evaluate.py
```

### Accuracy Results

| Metric | Value |
|--------|-------|
| **Index Format** | JSON (structured) |
| **Query Type** | Semantic |
| **Demo Accuracy** | **10/10 = 100%** |
| **Fine-Tune Citation Accuracy** | **100%** (20 samples) |
| **Search Ranking Accuracy** | **100%** (10 queries) |
| **Agent Citation Accuracy** | **90%** (ranking eval) |
| **Training Examples** | 80 |

> Previous accuracy before JSON sidecars + semantic query type: ~50% (PDF extraction with keyword search).

See [evaluation_results.md](evaluation_results.md) and [ranking_report.md](ranking_report.md) for full reports.

---

## Output Files

| File | Description |
|------|-------------|
| `data/filter-design-docs/FD-TC-*.pdf` | 100 generated filter design PDFs |
| `data/filter-design-docs/FD-TC-*.json` | 100 JSON sidecar files (structured metadata for AI Search) |
| `data/filter-design-docs/manifest.json` | Document index |
| `data/filter-design-docs/feedback_log.json` | Accumulated feedback entries |
| [evaluation_results.md](evaluation_results.md) | Fine-tuning evaluation report |
| [ranking_report.md](ranking_report.md) | Ranking & feedback evaluation report |
