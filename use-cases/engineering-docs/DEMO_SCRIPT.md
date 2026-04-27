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
| 1 | **Section-Level Chunking** | Each document section → separate search record (~200-800 chars instead of 5KB) |
| 2 | **Context Prefix** | Every chunk starts with `Document: MFG-TC-XXXX | Section: ...` for provenance |
| 3 | **Metadata Fields** | Filterable facets: `product_line`, `defect_type`, `technology_node`, `status` |
| 4 | **Custom Scoring Profile** | Title 3×, doc_number 2.5×, section_name 2×, content 1× |
| 5 | **Semantic Config + Keywords** | `document_number` and `section_name` as keyword fields for the semantic ranker |
| 6 | **200-char Overlap** | Large sections split with overlap to prevent information loss at boundaries |
| 7 | **English Microsoft Analyzer** | Lemmatization + compound word splitting for technical vocabulary |
| 8 | **BufferedSender** | Batch upload with auto-retry for 700+ chunks |
| 9 | **Daily Scheduled Indexer** | 8:00 AM PST automatic refresh from Blob Storage |
| 10 | **Managed Identity Auth** | No secrets — `ResourceId=` connection string for data source |

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
| Citation Accuracy | **90.0%** |
| Avg Tokens/Query | 222.8 |
| Training Examples | 539 |
| Evaluated Samples | 50 |

> **Key Point**: 90% citation accuracy from auto-generated training data — no manual labeling required. The 10% failures are typically cross-document queries where the model references related but different documents.

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

Example agent response:
> *"The Surfscan SP7 system is used for unpatterned wafer inspection to detect Crystal Originated Particles (COP) at the 5nm node. The capture rate was 97.2% with a nuisance rate of 2.1% [MFG-TC-0042.txt†engineering-docs-index]."*

---

## Closing: What the Customer Gets

1. **Reusable framework** — swap documents and configs, same pipeline works
2. **No vendor lock-in** — standard Azure services, managed identity, IaC-ready
3. **Production-grade search** — 10 implemented best practices, daily refresh, private networking
4. **Measurable accuracy** — fine-tuning pipeline with automatic evaluation
5. **All configuration-driven** — change `config/` files, not code
