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

## Act 3: AI Search Best Practices — Chunking Deep Dive (10 min)

### 3.1 — The chunking problem

Show the challenge with a full-document index:

```bash
python scripts/create_search_index.py
```

- A filter design PDF is ~2-3 pages (~4000 chars of extracted text)
- Querying "What is the insertion loss for Band 7 SAW filters?" returns the **entire PDF** as one result
- The agent has to parse through irrelevant sections (Procedure, Sign-off) to find the 100-char answer in Test Results

### 3.2 — Section-level chunking (the fix)

```bash
python scripts/chunk_and_index.py
```

Walk through what happens:

```
FD-TC-0001.pdf → 10 chunks:
  Document Header      (~500 chars)
  1. OBJECTIVE          (~300 chars)  ← "validates SAW filter for Band 7..."
  2. SCOPE              (~250 chars)  ← filter type, frequency, substrate
  3. DESIGN PARAMETERS  (~400 chars)  ← center freq, BW, IL target, Q factor
  4. TEST PROCEDURE     (~600 chars)
  5. ACCEPTANCE CRITERIA (~400 chars) ← IL ≤ 1.8 dB, RL ≥ 15 dB, ...
  6. TEST RESULTS       (~350 chars)  ← IL = 1.52 dB, RL = 18.3 dB, ...
  7. OBSERVATIONS       (~300 chars)
  8. CORRECTIVE ACTIONS (~200 chars)
  9. SIGN-OFF           (~150 chars)
```

**Key detail**: Each chunk carries a context prefix:
```
Document: FD-TC-0001 | SAW Filter - Band 7 for 5G NR Module
Section: 6. TEST RESULTS

Insertion Loss (meas): 1.52 dB
Return Loss (meas): 18.3 dB
Rejection (meas): 42.1 dB
...
```

> **Key Point**: Now when someone asks "What is the insertion loss for Band 7?", the search returns **just the Test Results section** (350 chars) instead of the full 4000-char document. The agent gets a precise, focused context.

### 3.3 — Custom scoring profile

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

> **Key Point**: Without scoring profiles, all fields have equal weight. With them, a query like "FD-TC-0015 insertion loss" correctly puts the Test Results section of FD-TC-0015 at the top instead of a random document that mentions "insertion loss" more frequently.

---

## Act 4: The Feedback Loop — 90% → 95% (10 min)

### 4.1 — Why 90% isn't enough

- At 90% accuracy, 1 in 10 queries returns an irrelevant or poorly ranked result
- For filter design, a wrong specification can lead to a $500K+ mask re-spin
- The semantic reranker is good but doesn't know which documents your team finds most useful

### 4.2 — How feedback-driven re-ranking works

```bash
python scripts/ranking_feedback.py
```

Walk through the **three-layer approach**:

**Layer 1: Semantic Reranking (baseline — 90%)**
- Azure AI Search's built-in semantic ranker scores results by meaning
- This is good but generic — it doesn't know your team's preferences

**Layer 2: Feedback Boost Map (the secret sauce)**
```python
# For each document, compute a boost from accumulated feedback
boost = 1.0 + (relevant_count - irrelevant_count) × 0.05
# Clamped to [0.8, 1.5]

# Final score = base_semantic_score × boost
```

Show `data/filter-design-docs/feedback_log.json`:
```json
{
  "timestamp": "2026-04-27T...",
  "query": "SAW filter insertion loss",
  "document_id": "FD-TC-0042.pdf",
  "relevant": true,
  "search_score": 8.234
}
```

> **Key Point**: Documents that users consistently find relevant get a **1.5× boost**, while irrelevant ones get suppressed (0.8×). Over time, the system learns which documents matter most for your team.

**Layer 3: Threshold Filtering**
- Results below relevance threshold (configurable, default 0.7) are dropped
- Reduces noise in the agent's context window
- Agent gets 5 highly relevant chunks instead of 10 mixed-quality ones

### 4.3 — Show the ranking report

Open `docs/ranking_report.md`:

| Metric | Baseline | With Feedback |
|--------|----------|---------------|
| Search Ranking Accuracy | 90% | 95%+ (target) |
| Agent Citation Accuracy | 90% | Improved with better context |
| Feedback Entries | 0 | 90+ (after synthetic generation) |

### 4.4 — The improvement flywheel

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

1. **90% → 95% accuracy pipeline** — systematic feedback loop, not just "add more data"
2. **Domain-specific agent** — understands RF filter terminology, never makes up specifications
3. **10 search best practices** — production-grade chunking, scoring, and indexing
4. **Self-improving system** — gets better with every query, no re-training needed
5. **Easy to customize** — change `config/agent_config.json` to adapt instructions, scoring weights, and thresholds
6. **Separate from other use cases** — isolated containers, indexes, and agents; clone just this folder
