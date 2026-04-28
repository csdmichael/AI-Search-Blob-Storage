# Use Case: RF Filter Design — Filter Design AI Assistant

> **Clone this folder** if you want to build a Foundry Agent that provides actionable filter design recommendations to RF engineers using Azure AI Search.

![Architecture](architecture.png)

## What This Use Case Does

- Generates **100 synthetic RF filter design documents** (.pdf) covering SAW, BAW, FBAR, TC-SAW, duplexer, and multiplexer designs across 5G NR, LTE, WiFi, and GPS bands
- Uploads them to a dedicated **Azure Blob Storage container** (`filter-design-docs`)
- Creates an **Azure AI Search index** with semantic + keyword search, refreshed daily at 8 AM PST
- Deploys a **Foundry Agent** (`Filter-Design-Agent`) that provides design recommendations exclusively from the indexed documents
- Implements a **ranking and feedback loop** to improve accuracy from 90% to 95%
- Evaluates and reports on ranking effectiveness

## Demo Focus: AI Search Best Practices, Chunking, Ranking & Feedback Loop

This use case demonstrates:

1. **Advanced AI Search** — section-level chunking, custom scoring profiles, metadata-enriched facets
2. **Feedback-Driven Re-Ranking** — collecting relevance feedback, computing boost maps, re-ranking search results
3. **Accuracy Improvement Pipeline** — from 90% baseline to 95% target through systematic feedback

See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for a step-by-step walkthrough.

## Quick Start

```bash
# Set the use case
export USE_CASE=filter_design     # Linux/Mac
$env:USE_CASE = "filter_design"   # PowerShell

# Generate 100 filter design PDFs
python scripts/generate_filter_docs.py

# Upload to Blob Storage
python scripts/upload_to_blob.py

# Create standard search index + indexer
python scripts/create_search_index.py

# Create chunked index with best practices
python scripts/chunk_and_index.py

# Create Foundry agent
export AZURE_AI_SEARCH_CONNECTION_NAME="ai-search-my"
python scripts/create_agent.py

# Run ranking & feedback evaluation
python scripts/ranking_feedback.py

# Test
python scripts/test_search.py
```

## Key Scripts

| Script | Purpose |
|--------|---------|
| `scripts/generate_filter_docs.py` | Generate 100 RF filter design `.pdf` files |
| `scripts/upload_to_blob.py` | Upload to `filter-design-docs` container |
| `scripts/create_search_index.py` | Create standard AI Search index + indexer |
| `scripts/chunk_and_index.py` | Section-level chunking with scoring profile |
| `scripts/create_agent.py` | Create `Filter-Design-Agent` in Foundry |
| `scripts/ranking_feedback.py` | Ranking & feedback loop evaluation |
| `scripts/test_search.py` | Run semantic + keyword search tests |

## Sample Prompts

### Semantic Search
- *"What filter designs target 5G NR sub-6 GHz bands?"*
- *"How does temperature affect SAW filter frequency stability?"*
- *"What are the acceptance criteria for BAW filter insertion loss?"*

### Keyword Search
- *"SAW filter Band 7 insertion loss"*
- *"BAW FBAR 5G NR n77"*
- *"FD-TC-0015"*

## JSON Sidecar Files

Each `.pdf` document is generated alongside a companion **`FD-TC-XXXX.json` sidecar** containing every field as structured data (filter type, frequency band, substrate material, all S-parameters, Q factor, temperature coefficient, and all document sections). These JSON files are:

- **Uploaded to Blob Storage** alongside the `.pdf` files by `upload_to_blob.py`
- **Used by `chunk_and_index.py`** as the authoritative source for the AI Search chunked index, eliminating lossy PDF text extraction
- **The primary reason demo accuracy improved from ~50% to 100%** (10/10 demo queries) and fine-tune citation accuracy reached 100% (20 samples): queries like "Which BAW filters have insertion loss below 1.5 dB?" now work because every field is a typed, searchable value

## Output Files

| File | Description |
|------|-------------|
| `data/filter-design-docs/FD-TC-*.pdf` | 100 generated filter design PDFs |
| `data/filter-design-docs/FD-TC-*.json` | 100 JSON sidecar files (structured metadata for AI Search) |
| `data/filter-design-docs/manifest.json` | Document index |
| `data/filter-design-docs/feedback_log.json` | Accumulated feedback entries |
| [`evaluation_results.md`](evaluation_results.md) | Fine-tuning evaluation report |
| [`ranking_report.md`](ranking_report.md) | Ranking & feedback evaluation report |
