# AI Search & Foundry Agent — Multi Use-Case Solution

An end-to-end, **reusable** solution that indexes engineering documents in Azure Blob Storage, creates Azure AI Search indexes with semantic and keyword search, and exposes Foundry Agents that answer questions exclusively from the indexed documents. The project supports **multiple use cases** via a single codebase driven by configuration.

## Pick Your Use Case

Each use case has its own **README, architecture diagram, and demo script** ready for customer presentations:

| Use Case | Folder | Demo Focus | Agent | Docs |
|----------|--------|-----------|-------|------|
| **Manufacturing Inspection** | [`docs/use-cases/engineering-docs/`](docs/use-cases/engineering-docs/) | AI Search best practices + **Fine-tuning & evaluation** | `Eng-Docs-Search-Agent` | 100 `.txt` + 100 `.json` (MFG-TC-XXXX) |
| **RF Filter Design** | [`docs/use-cases/filter-design/`](docs/use-cases/filter-design/) | AI Search best practices + **Ranking & feedback loop** (90%→95%) | `Filter-Design-Agent` | 100 `.pdf` + 100 `.json` (FD-TC-XXXX) |
| **Tax Exemption PDF Forms** | [`docs/use-cases/tax-pdf-forms/`](docs/use-cases/tax-pdf-forms/) | **Cosmos DB** → AI Search + section-level chunking | `Tax-PDF-Forms-Agent` | 388 PDFs from Cosmos DB (`taxforms/documents`) |
| **Engineering Design PPT** | [`docs/use-cases/eng-design-ppt/`](docs/use-cases/eng-design-ppt/) | **Cosmos DB** → AI Search + slide-level chunking | `Eng-Design-PPT-Agent` | 100 PPTs from Cosmos DB (`taxforms/documents`) |

> **Solution Engineers**: Go directly to the use case folder for a self-contained README with architecture, demo script, sample prompts, best practices, and setup instructions.

---

## Prerequisites

- **Azure CLI** installed and logged in (`az login`)
- **Python 3.10+** installed
- Azure subscription with the following resources already provisioned:
  - Storage Account: `aistoragemyaacoub` (with private VNET and private endpoint)
  - AI Search Service: `ai-search-my`
  - AI Foundry Project: `001-ai-poc / 001-ai-proj`
  - A deployed model (e.g., `gpt-4.1`) in the Foundry project

---

## Configuration

All settings are in the `config/` folder — **nothing is hardcoded** in scripts.

| Config File | Purpose |
|-------------|---------|
| [`config/azure_resources.json`](config/azure_resources.json) | Azure subscription, resource group, storage/search/foundry endpoints |
| [`config/agent_config.json`](config/agent_config.json) | Agent names, instructions, model deployment, fine-tuning params per use case |
| [`config/search_config.json`](config/search_config.json) | Index names, semantic configs, indexer schedule, chunking params, scoring weights |
| [`config/storage_config.json`](config/storage_config.json) | Container names per use case, upload settings |
| [`config/document_config.json`](config/document_config.json) | Document prefix, total count, classification, diagram settings per use case |
| [`config/prompts_config.json`](config/prompts_config.json) | Sample prompts per use case (keyword, semantic, agent) — shown in the UI and used for batch testing |
| [`config/__init__.py`](config/__init__.py) | Python config loader with `USE_CASE` env var support |

### Selecting a Use Case

Set the `USE_CASE` environment variable before running any script:

```bash
# Engineering docs (default)
export USE_CASE=engineering_docs

# Filter design
export USE_CASE=filter_design

# Tax Exemption PDF Forms (Cosmos DB)
export USE_CASE=tax_pdf_forms

# Engineering Design PPT (Cosmos DB)
export USE_CASE=eng_design_ppt
```

On Windows PowerShell:
```powershell
$env:USE_CASE = "filter_design"     # or tax_pdf_forms, eng_design_ppt
```

---

## Project Structure

```
AI-Search-Blob-Storage/
├── docs/
│   ├── Prompt.txt                        # Original project requirements
│   └── use-cases/
│       ├── engineering-docs/             # ★ Manufacturing inspection use case
│       │   ├── README.md                 # Self-contained guide: setup, demo, prompts, best practices
│       │   ├── evaluation_results.md     # Fine-tuning evaluation report
│       │   └── architecture.png          # Architecture diagram
│       └── filter-design/                # ★ RF filter design use case
│           ├── README.md                 # Self-contained guide: setup, demo, prompts, best practices
│           ├── evaluation_results.md     # Fine-tuning evaluation report
│           ├── ranking_report.md         # Ranking & feedback report
│           └── architecture.png          # Architecture diagram
├── .github/
│   └── workflows/
│       └── deploy.yml                    # GitHub Actions CI/CD (multi use-case)
├── config/
│   ├── __init__.py                       # Config loader (USE_CASE aware)
│   ├── azure_resources.json              # Azure resource IDs and endpoints
│   ├── agent_config.json                 # Agent instructions, fine-tuning per use case
│   ├── search_config.json                # Index names, scoring, chunking config
│   ├── storage_config.json               # Container names, upload settings
│   ├── document_config.json              # Doc prefix, count, classification per use case
│   └── prompts_config.json              # Sample prompts per use case (keyword, semantic, agent)
├── data/
│   ├── engineering-docs/                 # 100 manufacturing test cases (.txt)
│   │   ├── MFG-TC-0001.txt ... MFG-TC-0100.txt
│   │   ├── MFG-TC-0001.json ... MFG-TC-0100.json  (JSON sidecars)
│   │   └── manifest.json
│   └── filter-design-docs/              # 100 filter design specs (.pdf)
│       ├── FD-TC-0001.pdf ... FD-TC-0100.pdf
│       ├── FD-TC-0001.json ... FD-TC-0100.json    (JSON sidecars)
│       └── manifest.json
├── scripts/
│   ├── generate_docs.py                  # Generate manufacturing test case docs
│   ├── generate_filter_docs.py           # Generate filter design PDFs
│   ├── upload_to_blob.py                 # Upload docs to Blob Storage
│   ├── create_search_index.py            # Create AI Search index + indexer
│   ├── chunk_and_index.py                # Section-level chunking + enhanced index
│   ├── create_agent.py                   # Create Foundry agent
│   ├── fine_tune_and_evaluate.py         # Fine-tune model + evaluate accuracy
│   ├── ranking_feedback.py               # Ranking & feedback loop
│   ├── generate_architecture_diagram.py  # Generate all architecture PNGs
│   ├── test_search.py                    # Test semantic + keyword search
│   └── _list_connections.py              # Utility: list Foundry connections
├── requirements.txt
├── LICENSE
└── README.md
```

---

## References

- [Azure AI Search documentation](https://learn.microsoft.com/azure/search/search-what-is-azure-search)
- [Azure AI Search service limits, quotas, and capacity planning](https://learn.microsoft.com/azure/search/search-limits-quotas-capacity)
- [Azure AI Search reliability guidance](https://learn.microsoft.com/azure/reliability/reliability-ai-search)
- [Retrieval Augmented Generation (RAG) in Azure AI Search](https://learn.microsoft.com/azure/search/retrieval-augmented-generation-overview)
- [Azure AI Search — Integrated vectorization and chunking](https://learn.microsoft.com/azure/search/vector-search-integrated-vectorization)
- [Microsoft Foundry Agent Service overview](https://learn.microsoft.com/azure/foundry/agents/overview)
- [Quickstart: Create a Foundry Agent](https://learn.microsoft.com/azure/foundry/quickstarts/get-started-code)
- [Azure Blob Storage documentation](https://learn.microsoft.com/azure/storage/blobs/storage-blobs-introduction)
- [Semantic ranking in Azure AI Search](https://learn.microsoft.com/azure/search/semantic-search-overview)
- [Azure App Service — Deploy a containerized app](https://learn.microsoft.com/azure/app-service/tutorial-custom-container)
- [Azure Container Registry documentation](https://learn.microsoft.com/azure/container-registry/container-registry-intro)
- [GitHub Actions for Azure deployment](https://learn.microsoft.com/azure/developer/github/github-actions)
- [Azure AI Search + Foundry walkthrough video](https://youtu.be/yu4M7OKjnR4?si=ImvxddbPgz1j5KdR)

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Michael Yaacoub at Microsoft
