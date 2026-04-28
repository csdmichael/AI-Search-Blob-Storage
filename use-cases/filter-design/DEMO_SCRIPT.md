# Demo Script: RF Filter Design — AI Search Best Practices, Chunking & Feedback Loop

> **Audience**: Microsoft Solution Engineers presenting to RF/semiconductor filter design teams
> **Duration**: ~30 minutes
> **Prerequisites**: Azure resources provisioned, `pip install -r requirements.txt` done, `az login` completed

---

## Act 1: The Problem (2 min)

**Talking Points:**
- RF filter design teams manage hundreds of design specs, simulation reports, and characterization data across SAW, BAW, FBAR, and TC-SAW technologies
- Designers spend 20+ minutes hunting for specific S-parameter data, acceptance criteria, or past corrective actions across PDF documents
- Existing search gives ~90% accuracy but the team needs **95%+** for production use — wrong filter specs can cost $500K+ in re-spins
- Goal: Build an AI assistant that provides **actionable design recommendations** with cited sources, improving from 90% → 95% accuracy using a feedback loop

---

## Act 2: PDF Document Generation & Upload (5 min)

### 2.1 — Generate filter design documents

```bash
export USE_CASE=filter_design
python scripts/generate_filter_docs.py
```

Open `data/filter-design-docs/FD-TC-0001.pdf` and walk through the structure:
- **Professional PDF format** with headers, section titles, and structured data
- **9 sections**: Objective, Scope, Design Parameters, Test Procedure, Acceptance Criteria, Test Results, Observations, Corrective Actions, Sign-off
- **Domain-specific data**: center frequency, bandwidth, insertion loss, Q factor, substrate material, electrode stack, package type

> **Key Point**: Real filter design documents follow this structure — the generated PDFs are realistic enough for meaningful search evaluation.

### 2.2 — Upload to Blob Storage

```bash
python scripts/upload_to_blob.py
```

> **Key Point**: PDFs go to a **separate container** (`filter-design-docs`) from manufacturing docs (`engineering-docs`). Each use case is completely isolated at the storage level. Private endpoint ensures data never leaves the VNET.

---

## Act 3: AI Search Best Practices — JSON Index & Chunking Deep Dive (10 min)

### 3.1 — The accuracy problem with PDF extraction

Show the challenge with the standard PDF-based approach:

```bash
python scripts/create_search_index.py
```

- A filter design PDF is ~2-3 pages; text extraction via PyPDF is lossy and can drop or mangle numeric values
- Querying "What is the insertion loss for Band 7 SAW filters?" on raw PDFs returns the entire document with garbled numbers
- **This is why the original PDF-based approach gave only 50% agent citation accuracy**

### 3.2 — Switch to JSON index (the accuracy fix)

Generate structured JSON documents alongside PDFs:

```bash
export USE_CASE=filter_design
python scripts/generate_filter_docs.py
```

Each run now creates BOTH a PDF and a JSON file per document:
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

> **Key Point**: Every field is explicit and exact in JSON. There is no text extraction, no regex parsing, no chance of a number being misread from a PDF layout. This is the single biggest accuracy improvement.

### 3.3 — Section-level chunking from JSON

```bash
python scripts/chunk_and_index.py
```

`chunk_and_index.py` automatically detects JSON files and uses them in preference to PDFs:

```
FD-TC-0001.json → 10 chunks:
  Document Header      (~745 chars) ← ALL key metrics inline
  1. OBJECTIVE          (~300 chars)
  2. SCOPE              (~250 chars)
  3. DESIGN PARAMETERS  (~400 chars)
  4. TEST PROCEDURE     (~600 chars)
  5. ACCEPTANCE CRITERIA (~400 chars)
  6. TEST RESULTS       (~350 chars)
  7. OBSERVATIONS       (~300 chars)
  8. CORRECTIVE ACTIONS (~200 chars)
  9. SIGN-OFF           (~150 chars)
```

The Document Header chunk now contains ALL key measurements for fast single-field lookups:
```
Document Number: FD-TC-0001
Filter Type: SAW (Surface Acoustic Wave)
Frequency Band: Band 7 (2600 MHz)
Insertion Loss (meas, dB): 1.52
Return Loss (meas, dB): 18.3
Q Factor: 3350
...
```

> **Key Point**: A query like "What is the Q factor for FD-TC-0001?" retrieves just the Document Header chunk (745 chars) and returns the exact value instantly — no PDF parsing, no regex, no ambiguity.

### 3.4 — Custom scoring profile

Show the scoring weights:

| Field | Weight | Why |
|-------|--------|-----|
| `title` | **3.0×** | "SAW Filter - Band 7 for 5G NR Module" is the most descriptive |
| `document_number` | **2.5×** | When someone types "FD-TC-0015", that exact doc should rank #1 |
| `section_name` | **2.0×** | "Show me acceptance criteria" should boost chunks from that section |
| `content` | **1.0×** | Baseline for everything else |

**Live demo**: Run a search and show how scores change:
```bash
python scripts/test_search.py
```

> **Key Point**: The JSON-based index + semantic query type together raised agent citation accuracy from **50% to 90%+** on the 10 demo prompts.

---

## Act 4: The Feedback Loop — 50% → 90%+ (10 min)

### 4.1 — Why the original approach gave only 50%

**The two root causes of 50% agent citation accuracy:**

1. **Wrong query type**: The agent was using `SIMPLE` (keyword) queries. Queries like *"Which BAW filters have insertion loss below 1.5 dB?"* require semantic understanding — keyword search returns unrelated results.

2. **Disconnected feedback loop**: `ranking_feedback.py` was targeting the `standard_index` (full documents from blob), while the agent actually queries the `chunked_index` (section-level chunks). Feedback boosts were computed from a different index and never applied to agent queries — the feedback loop was effectively a no-op.

### 4.2 — The fixes applied

**Fix 1: Semantic query type** (in `create_agent.py`):
```python
# Before (keyword search only):
DEFAULT_QUERY_TYPE = AzureAISearchQueryType.SIMPLE

# After (meaning-aware reranking):
DEFAULT_QUERY_TYPE = AzureAISearchQueryType.SEMANTIC
```

**Fix 2: Feedback loop targets the correct index** (in `ranking_feedback.py`):
```python
# Before (standard blob-extracted index, wrong!):
INDEX_NAME = _uc_search["standard_index"]["name"]
doc_name = r.get("metadata_storage_name", "")

# After (chunked JSON index, correct):
INDEX_NAME = _uc_search["chunked_index"]["name"]
doc_name = r.get("source_file", r.get("document_number", ""))
```

**Fix 3: JSON-based index** (in `chunk_and_index.py`):
- `chunk_and_index.py` now auto-detects `.json` files and uses them over PDFs
- Explicit numeric fields in JSON ensure exact value retrieval

### 4.3 — How feedback-driven re-ranking works

```bash
python scripts/ranking_feedback.py
```

Walk through the **three-layer approach**:

**Layer 1: JSON Index + Semantic Reranking (baseline — 90%)**
- JSON-structured documents ensure all fields are queryable without text extraction
- Azure AI Search's semantic ranker scores results by meaning, not keywords

**Layer 2: Feedback Boost Map (continuous improvement)**
```python
# For each document, compute a boost from accumulated feedback
boost = 1.0 + (relevant_count - irrelevant_count) × 0.05
# Clamped to [0.8, 1.5]

# Final score = base_semantic_score × boost
```

Show `data/filter-design-docs/feedback_log.json`:
```json
{
  "timestamp": "2026-04-28T...",
  "query": "SAW filter insertion loss",
  "document_id": "FD-TC-0042.json",
  "relevant": true,
  "search_score": 8.234
}
```

> **Key Point**: Documents that users consistently find relevant get a **1.5× boost**, while irrelevant ones get suppressed (0.8×). Over time, the system learns which documents matter most for your team.

**Layer 3: Threshold Filtering**
- Results below relevance threshold (configurable, default 0.7) are dropped
- Reduces noise in the agent's context window
- Agent gets 5 highly relevant chunks instead of 10 mixed-quality ones

### 4.4 — Show the ranking report

Open `use-cases/filter-design/ranking_report.md`:

| Metric | Before | After |
|--------|--------|-------|
| Index Format | PDF (lossy extraction) | JSON (structured) |
| Query Type | SIMPLE (keyword) | SEMANTIC (meaning-aware) |
| Feedback Loop Target | standard_index (wrong) | chunked_index (correct) |
| Agent Citation Accuracy | 50% | **90%+** |

### 4.5 — The improvement flywheel

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

> **Key Point**: This is a **self-improving system**. Every time an engineer uses the agent and rates a result, the system gets smarter. No re-training required — just feedback accumulation.

---

## Act 5: The Agent in Action (3 min)

### 5.1 — Create the filter design agent

```bash
python scripts/create_agent.py
```

**Key differences from generic chat:**
- **Single tool**: Azure AI Search (no web search)
- **Strict instructions**: Never fabricate specifications — wrong numbers are dangerous in filter design
- **Always cite sources**: Every claim linked to a specific FD-TC document
- **Domain-specific**: Knows about insertion loss, S-parameters, Q factors, substrate materials

### 5.2 — Live queries

```bash
python scripts/test_search.py
```

### 5.3 — 10 Example Prompts with Expected Results

Use these during live demos. Each prompt is designed to test a different aspect of grounding accuracy.

| # | Prompt | Expected Result | What It Tests |
|---|--------|----------------|---------------|
| 1 | *"What is the measured insertion loss and return loss for FD-TC-0001?"* | Exact IL and RL values from Section 6 of FD-TC-0001 (e.g., IL 1.32 dB, RL 18.3 dB) with citation `[FD-TC-0001.pdf†...]` | Specific document lookup |
| 2 | *"Which TC-SAW filters target Band 7 and what were their results?"* | Lists FD-TC docs with filter_type=TC-SAW and frequency_band=Band 7, citing measured parameters | Faceted metadata query |
| 3 | *"What corrective actions are recommended in FD-TC-0005?"* | Quoted actions from Section 8 of FD-TC-0005 (e.g., optimize resonator geometry, re-run EM simulation) | Section-level grounding |
| 4 | *"What substrates are used for FBAR filter designs?"* | Lists substrate materials (AlN on Si, ScAlN, etc.) from FBAR documents with citations | Cross-document aggregation |
| 5 | *"Compare insertion loss across all filter designs that use LiNbO3 substrate."* | Table or list of IL values from LiNbO3-based designs, each cited by FD-TC number | Comparative analysis |
| 6 | *"What is the Q factor for FD-TC-0010?"* | Exact Q factor value from Design Parameters section of FD-TC-0010 | Single-field extraction |
| 7 | *"Which filter designs have FAIL status and why?"* | Lists failed designs with failure reasons from Observations/Corrective Actions sections | Status-filtered reasoning |
| 8 | *"What design tools were used for 5G NR n78 band filters?"* | Lists tools (e.g., Keysight ADS, COMSOL, Sonnet) from n78 band documents | Metadata + tool extraction |
| 9 | *"Show the acceptance criteria for duplexer isolation."* | Specific isolation thresholds (e.g., ≥ 45 dB) from duplexer test cases | Criteria extraction |
| 10 | *"What package types are used for BAW filters and what are their die sizes?"* | Lists package types (WLP, CSP, QFN) and die dimensions from BAW documents | Multi-field extraction |

**Demo tip**: For prompts 1, 3, and 6, open the actual PDF side-by-side to show the audience the agent's numbers match the source document exactly. This is the strongest proof of grounding.

---

## Closing: What the Customer Gets

1. **50% → 90%+ accuracy pipeline** — JSON index eliminates PDF extraction failures; semantic search handles natural language; fixed feedback loop amplifies what works
2. **Domain-specific agent** — understands RF filter terminology, never makes up specifications
3. **10 search best practices** — production-grade JSON indexing, semantic search, scoring, and chunking
4. **Self-improving system** — gets better with every query, no re-training needed
5. **Easy to customize** — change `config/agent_config.json` to adapt instructions, scoring weights, and thresholds
6. **Separate from other use cases** — isolated containers, indexes, and agents; clone just this folder
