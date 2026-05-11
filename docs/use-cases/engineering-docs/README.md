# Use Case: Manufacturing Inspection — Engineering Documents

> **Clone this folder** if you want to build a Foundry Agent that answers questions about semiconductor manufacturing inspection test cases using Azure AI Search.
>
> **Audience**: Microsoft Solution Engineers presenting to manufacturing/semiconductor customers
> **Duration**: ~30 minutes for full demo

---

## Architecture

![Architecture](architecture.png)

### Components

| Component | Resource | Description |
|-----------|----------|-------------|
| **Azure Blob Storage** | `aistoragemyaacoub` | Stores 100 `.txt` + 100 `.json` documents in the `engineering-docs` container |
| **JSON Sidecar Files** | `MFG-TC-XXXX.json` beside each `.txt` | Machine-readable structured metadata — eliminates lossy text extraction |
| **Azure AI Search** | `ai-search-my` | Indexes documents with semantic + keyword search; refreshes daily at 8 AM PST |
| **AI Foundry Agent** | `Eng-Docs-Search-Agent` | Answers queries using only AI Search — no web search or fabrication |
| **Managed Identity** | `DefaultAzureCredential` | All authentication uses managed identity — no keys or secrets |
| **Private VNET** | Existing VNET | Blob Storage and AI Search accessed via private endpoints |

### Deployed Web App URLs

| App | URL | Description |
|-----|-----|-------------|
| **API** | https://ai-search-agent-api.azurewebsites.net | FastAPI backend — proxies chat, batch, feedback, and prompt endpoints |
| **UI** | https://ai-search-agent-ui.azurewebsites.net | Ionic Angular chat UI — Copilot-style interface with use-case tabs |

---

## What This Use Case Demonstrates

1. **AI Search Best Practices** — section-level chunking, metadata facets, custom scoring profiles, semantic configuration
2. **Model Fine-Tuning** — auto-extracting Q&A pairs from documents, JSONL training data, fine-tuning with Azure AI Foundry, evaluation with citation accuracy metrics

---

## Basic SKU Search Capacity Recommendation

For this use case, start Azure AI Search on **Basic SKU with 1 partition and 3 replicas**.

| Setting | Recommendation | Why it fits this workload |
|---------|----------------|---------------------------|
| **Partitions** | **1** | The corpus is only 100 manufacturing documents plus chunked sections, so one partition is the most cost-efficient starting point while still leaving room for the standard and chunked indexes. Partitions primarily add storage and indexing throughput; this use case is query-heavy, not storage-heavy. |
| **Replicas** | **3** | Three replicas are the right Basic-tier default for demo and pilot traffic because replicas add query throughput and keep the service responsive while the daily indexer runs. This also aligns with Azure AI Search high-availability guidance for mixed query and indexing workloads. |

### Benefits of partitions and replicas

- **Partitions** increase storage capacity and parallel indexing throughput. For this small engineering-docs corpus, staying at one partition avoids unnecessary cost and keeps relevance tuning simple.
- **Replicas** increase query concurrency, reduce latency spikes during semantic queries, and let indexing jobs run with less impact on user traffic.
- **3 replicas on Basic** is the safer baseline for customer demos because it protects response quality when multiple users hit the agent while scheduled refresh is active.

Scale partitions first only if chunk counts or indexed storage grow materially. Scale replicas first if the agent starts seeing slower response times or concurrent-user pressure.

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
export USE_CASE=engineering_docs   # Linux/Mac
$env:USE_CASE = "engineering_docs" # PowerShell

# Generate 100 manufacturing test case documents (.txt + .json sidecars)
python scripts/generate_docs.py

# Upload to Blob Storage (engineering-docs container)
python scripts/upload_to_blob.py

# Create AI Search index and indexer (daily 8 AM PST refresh)
python scripts/create_search_index.py

# Create enhanced chunked index with scoring profile
python scripts/chunk_and_index.py

# Create Foundry agent (Eng-Docs-Search-Agent)
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
| `scripts/generate_docs.py` | Generate 100 manufacturing test case `.txt` + `.json` files |
| `scripts/upload_to_blob.py` | Upload to `engineering-docs` container |
| `scripts/create_search_index.py` | Create standard AI Search index + indexer |
| `scripts/chunk_and_index.py` | Section-level chunking with scoring profile |
| `scripts/create_agent.py` | Create `Eng-Docs-Search-Agent` in Foundry |
| `scripts/fine_tune_and_evaluate.py` | Fine-tune model + evaluate citation accuracy |
| `scripts/ranking_feedback.py` | Ranking & feedback loop evaluation |
| `scripts/test_search.py` | Run semantic + keyword search tests |

---

## Demo Script

### Act 1: The Problem (2 min)

**Talking Points:**
- Manufacturing teams have hundreds of engineering test case documents across fabs
- Engineers spend 30+ minutes searching for specific defect data, corrective actions, or acceptance criteria
- Traditional keyword search misses semantic intent — "What caused failures at 3nm?" returns nothing useful
- Goal: Build an AI agent that answers natural-language questions with cited sources in under 5 seconds

### Act 2: Document Generation & Indexing (5 min)

**2.1 — Show the raw documents**

```bash
export USE_CASE=engineering_docs
python scripts/generate_docs.py
```

Open `data/engineering-docs/MFG-TC-0001.txt` and walk through the structure:
- **9 sections**: Objective, Scope, Test Configuration, Procedure, Acceptance Criteria, Results, Observations, Corrective Actions, Sign-off
- **Structured metadata**: document number, product line, defect type, technology node, fab location, status

> **Key Point**: These mirror real manufacturing documents — structured sections with rich metadata.

**2.2 — Upload to Blob Storage**

```bash
python scripts/upload_to_blob.py
```

> **Key Point**: Uses **Managed Identity** (`DefaultAzureCredential`) — no connection strings or keys in code. Blob Storage is accessed via **private endpoint**.

### Act 3: AI Search Best Practices Deep Dive (10 min)

**3.1 — Standard Index (baseline)**

```bash
python scripts/create_search_index.py
```

- Creates a basic full-document index
- Good for keyword search, but semantic queries return entire 5KB documents
- Relevant answer may be buried in 200 chars within a 5000-char document

**3.2 — Chunked Index (best practice)**

```bash
python scripts/chunk_and_index.py
```

Walk through the **10 best practices** implemented (see [AI Search Best Practices](#ai-search-best-practices) below).

**How JSON-first indexing works:**

`generate_docs.py` emits both `.txt` and `.json` for each document. `chunk_and_index.py` automatically detects JSON files:

```python
json_files = [f for f in os.listdir(DATA_DIR) if f.startswith('MFG-TC') and f.endswith('.json')]
if json_files:
    chunks = chunk_document_json(doc_data, filename)
else:
    chunks = chunk_document(content, filename)
```

**Live demo**: Show the chunk distribution output:
```
Document Header: 100 chunks
1. OBJECTIVE: 100 chunks
2. SCOPE: 100 chunks
...
Total chunks: ~700+
```

> **Key Point**: Section-level chunking increased search accuracy from ~70% to ~90% because the agent gets precisely the relevant section, not the whole document.

**3.3 — Compare search results**

```bash
python scripts/test_search.py
```

Show side-by-side:
- **Keyword search**: Exact matches, fast, good for document IDs
- **Semantic search**: Natural language understanding, finds conceptually related documents

### Act 4: Fine-Tuning the Model (10 min)

**4.1 — Automatic training data extraction**

```bash
python scripts/fine_tune_and_evaluate.py
```

Walk through the pipeline:

**Step 1: Q&A Pair Generation**
- Script reads all 100 documents
- Extracts 5-7 Q&A pairs per document using regex patterns
- Questions cover: objectives, results, systems, acceptance criteria, observations, corrective actions
- Result: ~539 training pairs, ~135 validation pairs

Show a sample from `data/engineering-docs/fine_tuning_train.jsonl`:
```json
{
  "messages": [
    {"role": "system", "content": "You are a manufacturing engineering assistant..."},
    {"role": "user", "content": "What does test case MFG-TC-0042 cover?"},
    {"role": "assistant", "content": "Test case MFG-TC-0042 covers: Patterned Wafer Inspection..."}
  ]
}
```

**Step 2: Fine-Tuning**
- Uploads JSONL to Azure AI Foundry
- Creates fine-tuning job (3 epochs, auto batch/learning rate)
- If fine-tuning unavailable in region, gracefully falls back to base model evaluation

**Step 3: Evaluation**
- Tests 50 validation examples
- Measures **Citation Accuracy**: Does the model cite the correct MFG-TC document number?
- Measures **Token Efficiency**: Cost per query

**4.2 — Show evaluation results**

Open [evaluation_results.md](evaluation_results.md):

| Metric | Value |
|--------|-------|
| Citation Accuracy | **92.0%** |
| Avg Tokens/Query | 205.1 |
| Training Examples | 540 |
| Evaluated Samples | 50 |

> **Key Point**: 92% citation accuracy achieved with JSON-indexed documents. The previous 74% result was caused by cross-document queries hallucinating document numbers. JSON indexing provides explicit filterable fields that the search index can match on directly.

### Act 5: The Agent in Action (3 min)

**5.1 — Create the agent**

```bash
python scripts/create_agent.py
```

- Model: `gpt-4.1`
- Single tool: Azure AI Search (no web search)
- Strict instructions: no fabrication, always cite sources, respond with "not found" if no match
- All citations in `[MFG-TC-XXXX.txt†index]` format

**5.2 — Live queries**

```bash
python scripts/test_search.py
```

**5.3 — 10 Example Prompts with Expected Results**

| # | Prompt | Expected Result | What It Tests |
|---|--------|----------------|---------------|
| 1 | *"What is the capture rate and nuisance rate for MFG-TC-0001?"* | Exact numbers from the Test Results section with citation `[MFG-TC-0001.txt†...]` | Specific document lookup |
| 2 | *"Which test cases failed for 3nm technology node?"* | Lists MFG-TC documents with `FAIL` status at 3nm, citing each by number | Filtered semantic search |
| 3 | *"What corrective actions are recommended in MFG-TC-0005?"* | Quoted corrective actions from Section 8, not fabricated | Section-level grounding |
| 4 | *"What inspection systems are used for FinFET manufacturing?"* | Lists product lines from FinFET test cases with citations | Cross-document aggregation |
| 5 | *"What is the acceptance criteria for 5nm node patterned wafer inspection?"* | Specific thresholds from 5nm documents | Criteria extraction |
| 6 | *"Compare defect density across all test cases at Milpitas Fab A."* | Table of defect densities from Milpitas Fab A, each cited | Faceted metadata query |
| 7 | *"What is the scan speed and pixel size configured in MFG-TC-0010?"* | Exact values from the Test Configuration section | Configuration data retrieval |
| 8 | *"Which test cases have nuisance rate above 5% and what was recommended?"* | Documents where nuisance rate > 5% with corrective actions | Conditional reasoning |
| 9 | *"What defect types does the Surfscan SP7 detect?"* | Lists defect types from Surfscan SP7 test cases | Product-specific knowledge |
| 10 | *"Show me test results for post-CMP contamination inspection."* | Test results from post-CMP + contamination documents | Multi-field semantic match |

**Demo tip**: For prompts 1, 3, and 7, open the actual document side-by-side to show the audience the agent's numbers match exactly.

### Closing: What the Customer Gets

1. **Reusable framework** — swap documents and configs, same pipeline works
2. **No vendor lock-in** — standard Azure services, managed identity, IaC-ready
3. **Production-grade search** — 10 implemented best practices, daily refresh, private networking
4. **Measurable accuracy** — fine-tuning pipeline with automatic evaluation
5. **All configuration-driven** — change `config/` files, not code

---

## Sample Search Prompts

> **Tip**: These prompts are loaded from [`config/prompts_config.json`](../../../config/prompts_config.json). Add, remove, or edit prompts there to customize the UI and batch testing — no code changes needed.

### Semantic Search

| # | Prompt | Expected Results |
|---|--------|-----------------|
| 1 | *"What are the most common defect types found during wafer inspection?"* | Documents covering COP, scratches, haze, contamination |
| 2 | *"Which test cases failed and what corrective actions were recommended?"* | Test cases with FAIL status and their corrective actions |
| 3 | *"How does the Surfscan system detect crystal originated particles?"* | Surfscan SP7/SP5 test cases for COP/particle detection |
| 4 | *"What is the acceptance criteria for 5nm node patterned wafer inspection?"* | 5nm technology node test cases with acceptance criteria |
| 5 | *"Show me test results for post-CMP contamination inspection"* | Post-CMP process step documents covering contamination |
| 6 | *"What inspection systems are used for FinFET manufacturing?"* | FinFET-related test cases across product lines |
| 7 | *"Find documents about overlay metrology using the Archer system"* | Archer 700/750 overlay measurement test cases |
| 8 | *"What are the throughput requirements for 300mm wafer inspection?"* | 300mm wafer test cases with throughput criteria |

### Keyword Search

| # | Prompt | Expected Results |
|---|--------|-----------------|
| 1 | *"Surfscan SP7 particle detection"* | Surfscan SP7 particle detection documents |
| 2 | *"FinFET inspection post-etch defect"* | FinFET post-etch test cases |
| 3 | *"3nm technology node scratch detection"* | 3nm node scratch defect documents |
| 4 | *"CMP process wafer inspection FAIL"* | Failed CMP process test cases |
| 5 | *"MFG-TC-0042"* | Specific test case by document number |

---

## AI Search Best Practices

### 1. JSON-First Indexing

Reads `MFG-TC-XXXX.json` sidecar files when available — exact field values, no regex parsing. Each JSON contains all structured metadata fields (`document_number`, `title`, `status`, `product_line`, `target_defect`, `process_step`, `technology_node`, `fab_location`) plus all measurements and document sections.

### 2. Section-Level Chunking

Each document is split into section-level chunks (Objective, Scope, Test Configuration, etc.) instead of full-document indexing. Each chunk retains a context prefix (`Document: MFG-TC-XXXX | Title\nSection: ...`) for provenance.

### 3. Metadata-Enriched Fields

Every chunk includes structured filterable/facetable metadata:
```
document_number, title, status, product_line, target_defect,
process_step, technology_node, fab_location, section_name, source_file
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

Each `.txt` document is generated alongside a companion **`MFG-TC-XXXX.json` sidecar** containing every field as structured data (product line, defect type, process step, technology node, fab location, all measurements, and all document sections). These JSON files are:

- **Uploaded to Blob Storage** alongside the `.txt` files by `upload_to_blob.py`
- **Used by `chunk_and_index.py`** as the authoritative source for the AI Search chunked index, eliminating regex-based text parsing
- **The primary reason accuracy improved from ~70% to 92%+**: cross-document queries (e.g. "Which test cases involve the Teron SL650 system?") now work because `product_line` is a typed, filterable field

### Why JSON Sidecars?

| Without JSON (TXT extraction) | With JSON Sidecars |
|---|---|
| Text extraction relies on regex parsing | All fields are exact — no parsing errors |
| Numbers can be mis-read or truncated | Numeric fields stored as typed values |
| Cross-document queries often fail | Filterable/facetable metadata fields enable precise cross-document queries |
| Agent accuracy: ~70% | Agent accuracy: **92%** |

---

## Fine-Tuning & Evaluation

Q&A pairs are auto-extracted from documents. The model is fine-tuned (or evaluated with the base model if fine-tuning is unavailable in the region).

```bash
USE_CASE=engineering_docs python scripts/fine_tune_and_evaluate.py
```

### Accuracy Results

| Metric | Value |
|--------|-------|
| **Index Format** | JSON (structured) |
| **Query Type** | Semantic |
| **Demo Accuracy** | **10/10 = 100%** |
| **Fine-Tune Citation Accuracy** | **92%** (50 samples) |
| **Training Examples** | 540 |
| **Avg Tokens/Query** | 205.1 |

> Previous accuracy before JSON sidecars + semantic query type: ~70% (TXT extraction with keyword search).

See [evaluation_results.md](evaluation_results.md) for the full detailed report.

---

## Output Files

| File | Description |
|------|-------------|
| `data/engineering-docs/MFG-TC-*.txt` | 100 generated test case documents |
| `data/engineering-docs/MFG-TC-*.json` | 100 JSON sidecar files (structured metadata for AI Search) |
| `data/engineering-docs/manifest.json` | Document index |
| `data/engineering-docs/fine_tuning_train.jsonl` | Training data (~539 Q&A pairs) |
| `data/engineering-docs/fine_tuning_validation.jsonl` | Validation data (~135 Q&A pairs) |
| `data/engineering-docs/evaluation_metrics.json` | Raw evaluation metrics |
| [evaluation_results.md](evaluation_results.md) | Human-readable evaluation report |
