# Demo Script: Manufacturing Inspection — Fine-Tuning & AI Search Best Practices

> **Audience**: Microsoft Solution Engineers presenting to manufacturing/semiconductor customers
> **Duration**: ~30 minutes
> **Prerequisites**: Azure resources provisioned, `pip install -r requirements.txt` done, `az login` completed

---

## Act 1: The Problem (2 min)

**Talking Points:**
- Manufacturing teams have hundreds of engineering test case documents across fabs
- Engineers spend 30+ minutes searching for specific defect data, corrective actions, or acceptance criteria
- Traditional keyword search misses semantic intent — "What caused failures at 3nm?" returns nothing useful
- Goal: Build an AI agent that answers natural-language questions with cited sources in under 5 seconds

---

## Act 2: Document Generation & Indexing (5 min)

### 2.1 — Show the raw documents

```bash
export USE_CASE=engineering_docs
python scripts/generate_docs.py
```

Open `data/engineering-docs/MFG-TC-0001.txt` and walk through the structure:
- **9 sections**: Objective, Scope, Test Configuration, Procedure, Acceptance Criteria, Results, Observations, Corrective Actions, Sign-off
- **Structured metadata**: document number, product line, defect type, technology node, fab location, status

> **Key Point**: These mirror real manufacturing documents — structured sections with rich metadata.

### 2.2 — Upload to Blob Storage

```bash
python scripts/upload_to_blob.py
```

> **Key Point**: Uses **Managed Identity** (`DefaultAzureCredential`) — no connection strings or keys in code. Blob Storage is accessed via **private endpoint**.

---

## Act 3: AI Search Best Practices Deep Dive (10 min)

### 3.1 — Standard Index (baseline)

```bash
python scripts/create_search_index.py
```

- Creates a basic full-document index
- Good for keyword search, but semantic queries return entire 5KB documents
- Relevant answer may be buried in 200 chars within a 5000-char document

### 3.2 — Chunked Index (best practice)

```bash
python scripts/chunk_and_index.py
```

Walk through **10 best practices** implemented:

| # | Practice | What It Does |
|---|----------|-------------|
| 1 | **JSON-First Indexing** | Reads `MFG-TC-XXXX.json` files when available — exact field values, no regex parsing |
| 2 | **Section-Level Chunking** | Each document section → separate search record (~200-800 chars instead of 5KB) |
| 3 | **Context Prefix** | Every chunk starts with `Document: MFG-TC-XXXX | Section: ...` for provenance |
| 4 | **Metadata Fields** | Filterable facets: `product_line`, `defect_type`, `technology_node`, `status` |
| 5 | **Custom Scoring Profile** | Title 3×, doc_number 2.5×, section_name 2×, content 1× |
| 6 | **Semantic Config + Keywords** | `document_number` and `section_name` as keyword fields for the semantic ranker |
| 7 | **200-char Overlap** | Large sections split with overlap to prevent information loss at boundaries |
| 8 | **English Microsoft Analyzer** | Lemmatization + compound word splitting for technical vocabulary |
| 9 | **BufferedSender** | Batch upload with auto-retry for 700+ chunks |
| 10 | **Managed Identity Auth** | No secrets — `ResourceId=` connection string for data source |

**How JSON-first indexing works:**

`generate_docs.py` now emits both `.txt` and `.json` for each document. `chunk_and_index.py` automatically detects JSON files:

```python
# chunk_and_index.py auto-detects JSON files
json_files = [f for f in os.listdir(DATA_DIR) if f.startswith('MFG-TC') and f.endswith('.json')]
if json_files:
    # Use JSON: direct field access, no regex
    chunks = chunk_document_json(doc_data, filename)
else:
    # Fall back to TXT parsing
    chunks = chunk_document(content, filename)
```

The JSON header chunk includes all key metrics for instant single-field retrieval:
```
Document Number: MFG-TC-0001
Product Line: Surfscan SP7
Target Defect: Pattern Defects
Technology Node: 5nm
Fab Location: Milpitas Fab A
Capture Rate (%): 95.2
Nuisance Rate (%): 2.3
```

> **Key Point**: JSON indexing eliminated the cross-document query failures that caused 26% of citation errors. Queries like "What test cases involve the Surfscan SP7?" now correctly filter by the `product_line` field instead of relying on keyword matches in extracted text.

**Live demo**: Show the chunk distribution output:
```
Document Header: 100 chunks
1. OBJECTIVE: 100 chunks
2. SCOPE: 100 chunks
...
Total chunks: ~700+
```

> **Key Point**: Section-level chunking increased search accuracy from ~70% to ~90% because the agent gets precisely the relevant section, not the whole document.

### 3.3 — Compare search results

```bash
python scripts/test_search.py
```

Show side-by-side:
- **Keyword search**: Exact matches, fast, good for document IDs
- **Semantic search**: Natural language understanding, finds conceptually related documents

---

## Act 4: Fine-Tuning the Model (10 min)

### 4.1 — Automatic training data extraction

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

### 4.2 — Show evaluation results

Open `docs/evaluation_results.md`:

| Metric | Value |
|--------|-------|
| Citation Accuracy | **92.0%** |
| Avg Tokens/Query | 205.1 |
| Training Examples | 540 |
| Evaluated Samples | 50 |

> **Key Point**: 92% citation accuracy achieved with JSON-indexed documents. The previous 74% result was caused by cross-document queries ("What test cases involve the Teron SL650?") hallucinating document numbers. JSON indexing provides explicit filterable fields (`product_line`, `target_defect`, `technology_node`) that the search index can match on directly, not just keyword-match in body text.

---

## Act 5: The Agent in Action (3 min)

### 5.1 — Create the agent

```bash
python scripts/create_agent.py
```

**Key agent configuration:**
- Model: `gpt-4.1`
- Single tool: Azure AI Search (no web search)
- Strict instructions: no fabrication, always cite sources, respond with "not found" if no match
- All citations in `[MFG-TC-XXXX.txt†index]` format

### 5.2 — Live queries

Run the test script and show agent responses:

```bash
python scripts/test_search.py
```

### 5.3 — 10 Example Prompts with Expected Results

Use these during live demos. Each prompt is designed to test a different aspect of grounding accuracy.

| # | Prompt | Expected Result | What It Tests |
|---|--------|----------------|---------------|
| 1 | *"What is the capture rate and nuisance rate for MFG-TC-0001?"* | Exact numbers from the Test Results section of MFG-TC-0001 (e.g., capture rate 87.5%, nuisance rate 3.7%) with citation `[MFG-TC-0001.txt†...]` | Specific document lookup |
| 2 | *"Which test cases failed for 3nm technology node?"* | Lists MFG-TC documents with `FAIL` status at 3nm, citing each by number | Filtered semantic search |
| 3 | *"What corrective actions are recommended in MFG-TC-0005?"* | Quoted corrective actions from Section 8 of MFG-TC-0005, not fabricated | Section-level grounding |
| 4 | *"What inspection systems are used for FinFET manufacturing?"* | Lists product lines (e.g., Surfscan, Archer, Puma) from FinFET test cases with citations | Cross-document aggregation |
| 5 | *"What is the acceptance criteria for 5nm node patterned wafer inspection?"* | Specific thresholds (capture rate ≥ X%, throughput ≥ Y wafers/hr) from 5nm documents | Criteria extraction |
| 6 | *"Compare defect density across all test cases at Milpitas Fab A."* | Table or list of defect densities from Milpitas Fab A documents, each cited | Faceted metadata query |
| 7 | *"What is the scan speed and pixel size configured in MFG-TC-0010?"* | Exact values from the Test Configuration section of MFG-TC-0010 | Configuration data retrieval |
| 8 | *"Which test cases have nuisance rate above 5% and what was recommended?"* | Documents where nuisance rate > 5% with corrective actions, each cited | Conditional reasoning |
| 9 | *"What defect types does the Surfscan SP7 detect?"* | Lists defect types (COP, scratches, particles, etc.) from Surfscan SP7 test cases | Product-specific knowledge |
| 10 | *"Show me test results for post-CMP contamination inspection."* | Test results (defect count, capture rate, status) from post-CMP + contamination documents | Multi-field semantic match |

**Demo tip**: For prompts 1, 3, and 7, open the actual document side-by-side to show the audience the agent's numbers match exactly.

---

## Closing: What the Customer Gets

1. **Reusable framework** — swap documents and configs, same pipeline works
2. **No vendor lock-in** — standard Azure services, managed identity, IaC-ready
3. **Production-grade search** — 10 implemented best practices, daily refresh, private networking
4. **Measurable accuracy** — fine-tuning pipeline with automatic evaluation
5. **All configuration-driven** — change `config/` files, not code
