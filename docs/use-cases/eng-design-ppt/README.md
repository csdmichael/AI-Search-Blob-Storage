# Use Case: Engineering Design PPT (Cosmos DB)

> **Foundry Agent** that answers questions about engineering design presentations (PPT/PPTX) stored in Azure Cosmos DB, using Azure AI Search as the sole knowledge source.
>
> **Data Source**: Cosmos DB (`cosmos-ai-poc` / `taxform` / `documents`) — filtered for `.ppt` / `.pptx` files
> **Audience**: Engineering teams, design reviewers, project managers

---

## Architecture

![Engineering Design Presentations — Architecture Diagram](architecture.png)

### Components

| Component | Resource | Description |
|-----------|----------|-------------|
| **Azure Cosmos DB** | `cosmos-ai-poc` | Source database — `taxform` database, `documents` container, filtered for PPT files |
| **Azure AI Search** | `ai-search-my` | Indexes Cosmos DB documents with semantic + keyword search; daily refresh at 8 AM PST |
| **Chunked Index** | `eng-design-ppt-chunked-index` | Section-level chunks with scoring profile boosting title, design type, project name |
| **AI Foundry Agent** | `Eng-Design-PPT-Agent` | Answers queries using only AI Search — no web search or fabrication |
| **Managed Identity** | `DefaultAzureCredential` | All authentication uses managed identity — no keys or secrets |
| **Private VNET** | Existing VNET | Cosmos DB accessed via private endpoints |

### Deployed Web App URLs

| App | URL | Description |
|-----|-----|-------------|
| **API** | https://ai-search-agent-api.azurewebsites.net | FastAPI backend — proxies chat, batch, feedback, and prompt endpoints |
| **UI** | https://ai-search-agent-ui.azurewebsites.net | Ionic Angular chat UI — Copilot-style interface with use-case tabs |

---

## What This Use Case Demonstrates

1. **Cosmos DB → AI Search Integration** — Indexer connects to Cosmos DB with managed identity, filters PPT documents, and indexes them with daily refresh
2. **Slide-Level Chunking** — Presentations are chunked by slide/section for granular search results
3. **Custom Scoring Profile** — Title (3×), design type (2.5×), project name (2×), section name (2×), content (1×)
4. **Strict Grounding** — Agent only uses AI Search index; never fabricates information
5. **Ranking & Feedback Loop** — Feedback-driven re-ranking to improve accuracy to 95%+

---

## Quick Start

### Prerequisites

- **Azure CLI** installed and logged in (`az login`)
- **Python 3.10+** with `pip install -r requirements.txt`
- Azure Cosmos DB with `taxform` database and `documents` container containing PPT presentation data
- Managed identity with **Cosmos DB Built-in Data Contributor** role (`00000000-0000-0000-0000-000000000002`) on the Cosmos DB account — required for both the **App Service** and **AI Search** managed identities
- AI Search service managed identity also needs the same **Cosmos DB Built-in Data Contributor** role

### Setup Commands

```bash
# 1a. Assign Cosmos DB Data Contributor to AI Search managed identity
az cosmosdb sql role assignment create \
  --account-name cosmos-ai-poc \
  --resource-group ai-myaacoub \
  --role-definition-id "00000000-0000-0000-0000-000000000002" \
  --scope "/" \
  --principal-id <AI_SEARCH_MANAGED_IDENTITY_OBJECT_ID>

# 1b. Assign Cosmos DB Data Contributor to App Service managed identity
az cosmosdb sql role assignment create \
  --account-name cosmos-ai-poc \
  --resource-group ai-myaacoub \
  --role-definition-id "00000000-0000-0000-0000-000000000002" \
  --scope "/" \
  --principal-id <APP_SERVICE_MANAGED_IDENTITY_OBJECT_ID>

# 2. Set the use case
export USE_CASE=eng_design_ppt          # Linux/Mac
$env:USE_CASE = "eng_design_ppt"        # PowerShell

# 3. Create AI Search index with Cosmos DB data source and indexer
python scripts/create_cosmosdb_search_index.py

# 4. Create enhanced chunked index with scoring profile
python scripts/chunk_and_index_cosmosdb.py

# 5. Create Foundry agent (Eng-Design-PPT-Agent)
export AZURE_AI_SEARCH_CONNECTION_NAME="ai-search-my"
python scripts/create_agent.py

# 6. Run ranking & feedback evaluation
python scripts/ranking_feedback.py
```

### Managed Identity Setup

> **Important**: Both the AI Search service and the API App Service need **Cosmos DB Built-in Data Contributor** (`00000000-0000-0000-0000-000000000002`) role. The Data Reader role (`...0001`) is insufficient — the API requires `readMetadata` which is only in the Data Contributor role.

```bash
# Get the AI Search service principal ID
SEARCH_PRINCIPAL_ID=$(az search service show \
  --name ai-search-my \
  --resource-group ai-myaacoub \
  --query identity.principalId -o tsv)

# Assign Cosmos DB Built-in Data Contributor to AI Search
az cosmosdb sql role assignment create \
  --account-name cosmos-ai-poc \
  --resource-group ai-myaacoub \
  --role-definition-id 00000000-0000-0000-0000-000000000002 \
  --scope "/" \
  --principal-id $SEARCH_PRINCIPAL_ID

# Get the App Service managed identity principal ID
APP_PRINCIPAL_ID=$(az webapp identity show \
  --name ai-search-agent-api \
  --resource-group ai-myaacoub \
  --query principalId -o tsv)

# Assign Cosmos DB Built-in Data Contributor to App Service
az cosmosdb sql role assignment create \
  --account-name cosmos-ai-poc \
  --resource-group ai-myaacoub \
  --role-definition-id 00000000-0000-0000-0000-000000000002 \
  --scope "/" \
  --principal-id $APP_PRINCIPAL_ID
```

---

## AI Search Best Practices

| Practice | Implementation |
|----------|---------------|
| **Cosmos DB Data Source** | Managed identity connection with SQL API query filtering for `.ppt` / `.pptx` files |
| **Slide-Level Chunking** | Each slide/section becomes a separate search chunk for precise retrieval |
| **Custom Scoring Profile** | Title (3×), design type (2.5×), project name (2×) boost relevant metadata |
| **Semantic Configuration** | Content as primary field, title as title field, design type and project name as keywords |
| **Daily Refresh** | Indexer runs daily at 8 AM PST to pick up new/updated documents |
| **Overlap Context** | 200-character overlap between chunks preserves context at boundaries |

---

## Sample Prompts

### Semantic Search
- "What are the key design specifications in the latest engineering review?"
- "Which presentations cover system architecture decisions?"
- "What trade-off analyses were performed for material selection?"
- "How are thermal constraints addressed in the design?"
- "What project milestones are documented in the presentations?"

### Keyword Search
- "engineering design review presentation"
- "system architecture diagram"
- "design specification requirements"
- "thermal analysis simulation"
- "manufacturing process flow"

### Agent Queries
- "What are the key design specifications in the latest engineering review?"
- "Which presentations cover system architecture decisions?"
- "List all design reviews that identified critical risks."
- "What trade-off analyses were performed for material selection?"
- "What project milestones are documented in the presentations?"

---

## Ranking & Feedback Loop

The ranking and feedback system improves accuracy from baseline 90% to 95%+:

1. **Feedback Collection**: User feedback (relevant/irrelevant) per query-document pair
2. **Re-Ranking**: Documents with positive feedback get boost factors (up to 1.5×)
3. **Relevance Threshold**: Results below 0.7 relevance score are suppressed
4. **Evaluation**: Periodic accuracy evaluation against curated query sets

Run the feedback evaluation:
```bash
$env:USE_CASE = "eng_design_ppt"
python scripts/ranking_feedback.py
```

Results are saved to `docs/use-cases/eng-design-ppt/ranking_report.md`.

---

## Configuration Files

| File | Purpose |
|------|---------|
| [config/azure_resources.json](../../config/azure_resources.json) | Cosmos DB account, AI Search, Foundry endpoint |
| [config/search_config.json](../../config/search_config.json) | Index names, semantic configs, indexer settings, Cosmos DB query filter |
| [config/agent_config.json](../../config/agent_config.json) | Agent name, model, instructions, fine-tuning settings |
| [config/document_config.json](../../config/document_config.json) | Document prefix, file format, Cosmos DB filter type |
| [config/prompts_config.json](../../config/prompts_config.json) | Sample prompts for testing (keyword, semantic, agent) |
