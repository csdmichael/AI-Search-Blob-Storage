# Use Case: Tax Exemption PDF Forms (Cosmos DB)

> **Foundry Agent** that answers questions about tax exemption PDF forms stored in Azure Cosmos DB, using Azure AI Search as the sole knowledge source.
>
> **Data Source**: Cosmos DB (`cosmos-ai-poc` / `taxform` / `documents`) — filtered for `.pdf` files
> **Audience**: Tax compliance teams, finance departments, audit reviewers

---

## Architecture

![Architecture](architecture.png)

### Components

| Component | Resource | Description |
|-----------|----------|-------------|
| **Azure Cosmos DB** | `cosmos-ai-poc` | Source database — `taxform` database, `documents` container, filtered for PDF files |
| **Azure AI Search** | `ai-search-my` | Indexes Cosmos DB documents with semantic + keyword search; daily refresh at 8 AM PST |
| **Chunked Index** | `tax-pdf-forms-chunked-index` | Section-level chunks with scoring profile boosting title, form type, jurisdiction |
| **AI Foundry Agent** | `Tax-PDF-Forms-Agent` | Answers queries using only AI Search — no web search or fabrication |
| **Managed Identity** | `DefaultAzureCredential` | All authentication uses managed identity — no keys or secrets |
| **Private VNET** | Existing VNET | Cosmos DB accessed via private endpoints |

### Deployed Web App URLs

| App | URL | Description |
|-----|-----|-------------|
| **API** | https://ai-search-agent-api.azurewebsites.net | FastAPI backend — proxies chat, batch, feedback, and prompt endpoints |
| **UI** | https://ai-search-agent-ui.azurewebsites.net | Ionic Angular chat UI — Copilot-style interface with use-case tabs |

---

## What This Use Case Demonstrates

1. **Cosmos DB → AI Search Integration** — Indexer connects to Cosmos DB with managed identity, filters PDF documents, and indexes them with daily refresh
2. **Section-Level Chunking** — Documents are chunked by section for granular search results
3. **Custom Scoring Profile** — Title (3×), form type (2.5×), jurisdiction (2×), section name (2×), content (1×)
4. **Strict Grounding** — Agent only uses AI Search index; never fabricates information
5. **Ranking & Feedback Loop** — Feedback-driven re-ranking to improve accuracy to 95%+

---

## Quick Start

### Prerequisites

- **Azure CLI** installed and logged in (`az login`)
- **Python 3.10+** with `pip install -r requirements.txt`
- Azure Cosmos DB with `taxform` database and `documents` container containing PDF form data
- Managed identity with **Cosmos DB Built-in Data Contributor** role (`00000000-0000-0000-0000-000000000002`) on the Cosmos DB account — required for both the **App Service** and **AI Search** managed identities
- AI Search service managed identity also needs the same **Cosmos DB Built-in Data Contributor** role
- API App Service managed identity also needs **Storage Blob Data Reader** on storage account `aistoragemyaacoub` so document originals can be streamed from Blob Storage
- If the storage account uses a private endpoint with `publicNetworkAccess` disabled, the API App Service must be integrated with the same VNet and an App Service delegated subnet so it can resolve and reach `privatelink.blob.core.windows.net`

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
export USE_CASE=tax_pdf_forms          # Linux/Mac
$env:USE_CASE = "tax_pdf_forms"        # PowerShell

# 3. Create AI Search index with Cosmos DB data source and indexer
python scripts/create_cosmosdb_search_index.py

# 4. Create enhanced chunked index with scoring profile
python scripts/chunk_and_index_cosmosdb.py

# 5. Create Foundry agent (Tax-PDF-Forms-Agent)
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

# Assign Storage Blob Data Reader to App Service
az role assignment create \
  --assignee-object-id $APP_PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Reader" \
  --scope "/subscriptions/86b37969-9445-49cf-b03f-d8866235171c/resourceGroups/ai-myaacoub/providers/Microsoft.Storage/storageAccounts/aistoragemyaacoub"

# If Blob Storage is private-endpoint only, integrate the API App Service with the app subnet
az webapp vnet-integration add \
  --name ai-search-agent-api \
  --resource-group ai-myaacoub \
  --vnet vnet-salespoc-westus2 \
  --subnet snet-appservice

az webapp config appsettings set \
  --name ai-search-agent-api \
  --resource-group ai-myaacoub \
  --settings WEBSITE_VNET_ROUTE_ALL=1
```

---

## AI Search Best Practices

| Practice | Implementation |
|----------|---------------|
| **Cosmos DB Data Source** | Managed identity connection with SQL API query filtering for `.pdf` files |
| **Section-Level Chunking** | Each document section becomes a separate search chunk for precise retrieval |
| **Custom Scoring Profile** | Title (3×), form type (2.5×), jurisdiction (2×) boost relevant metadata |
| **Semantic Configuration** | Content as primary field, title as title field, form type and jurisdiction as keywords |
| **Daily Refresh** | Indexer runs daily at 8 AM PST to pick up new/updated documents |
| **Overlap Context** | 200-character overlap between chunks preserves context at boundaries |

---

## Sample Prompts

### Semantic Search
- "What forms are required for sales tax exemption?"
- "How do I file for a nonprofit tax exemption certificate?"
- "What are the deadlines for property tax exemption applications?"
- "Which states accept multi-jurisdiction exemption certificates?"
- "What documentation is needed for a resale certificate?"

### Keyword Search
- "tax exemption certificate form"
- "sales tax exemption"
- "501(c)(3) nonprofit exemption"
- "resale certificate"
- "multi-state tax exemption"

### Agent Queries
- "What tax exemption forms are available for nonprofits?"
- "What is the filing deadline for sales tax exemption in Texas?"
- "List all forms required for property tax exemption."
- "What are the eligibility requirements for agricultural exemption?"
- "How do I renew an expiring tax exemption certificate?"

---

## Ranking & Feedback Loop

The ranking and feedback system improves accuracy from baseline 90% to 95%+:

1. **Feedback Collection**: User feedback (relevant/irrelevant) per query-document pair
2. **Re-Ranking**: Documents with positive feedback get boost factors (up to 1.5×)
3. **Relevance Threshold**: Results below 0.7 relevance score are suppressed
4. **Evaluation**: Periodic accuracy evaluation against curated query sets

Run the feedback evaluation:
```bash
$env:USE_CASE = "tax_pdf_forms"
python scripts/ranking_feedback.py
```

Results are saved to `docs/use-cases/tax-pdf-forms/ranking_report.md`.

---

## Configuration Files

| File | Purpose |
|------|---------|
| [config/azure_resources.json](../../config/azure_resources.json) | Cosmos DB account, AI Search, Foundry endpoint |
| [config/search_config.json](../../config/search_config.json) | Index names, semantic configs, indexer settings, Cosmos DB query filter |
| [config/agent_config.json](../../config/agent_config.json) | Agent name, model, instructions, fine-tuning settings |
| [config/document_config.json](../../config/document_config.json) | Document prefix, file format, Cosmos DB filter type |
| [config/prompts_config.json](../../config/prompts_config.json) | Sample prompts for testing (keyword, semantic, agent) |
