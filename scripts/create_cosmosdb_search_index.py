"""
Create an Azure AI Search index with a Cosmos DB data source, indexer,
and schedule it to refresh daily at 8 AM PST.

Supports both semantic and keyword search.
Uses managed identity for authentication.
Filters documents by file type (pdf for tax forms, ppt for engineering design).

Set USE_CASE env var to select: tax_pdf_forms or eng_design_ppt
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField,
    SearchIndexerDataSourceConnection,
    SearchIndexerDataContainer,
    SearchIndexer,
    IndexingSchedule,
    FieldMapping,
)

_res = config.azure_resources()
_uc_search = config.uc_search_config()
_global_search = config.search_config()
_cosmosdb = config.cosmosdb_config()

SEARCH_ENDPOINT = config.search_endpoint()
INDEX_NAME = _uc_search["standard_index"]["name"]
SEMANTIC_CONFIG_NAME = _uc_search["standard_index"]["semantic_config_name"]
INDEXER_NAME = _uc_search["indexer"]["name"]
DATA_SOURCE_NAME = _uc_search["indexer"]["data_source_name"]
INDEXER_QUERY = _uc_search["indexer"].get("query", "")

COSMOSDB_ACCOUNT_NAME = _cosmosdb["account_name"]
COSMOSDB_DATABASE = _cosmosdb["database_name"]
COSMOSDB_CONTAINER = _cosmosdb["container_name"]
COSMOSDB_RESOURCE_ID = config.cosmosdb_resource_id()


def create_index(index_client: SearchIndexClient):
    """Create the search index with semantic configuration for Cosmos DB documents."""
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            analyzer_name="en.microsoft",
        ),
        SearchableField(
            name="fileName",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="state",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SearchableField(
            name="stateName",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="status",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="overallConfidence",
            type=SearchFieldDataType.Double,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="confidenceCategory",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SearchableField(
            name="confidenceLabel",
            type=SearchFieldDataType.String,
        ),
        SimpleField(
            name="totalFields",
            type=SearchFieldDataType.Int32,
            filterable=True,
        ),
        SimpleField(
            name="totalSections",
            type=SearchFieldDataType.Int32,
            filterable=True,
        ),
        SimpleField(
            name="uploadedAt",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="parsedAt",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
    ]

    semantic_config = SemanticConfiguration(
        name=SEMANTIC_CONFIG_NAME,
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="content")],
            title_field=SemanticField(field_name="fileName"),
            keywords_fields=[
                SemanticField(field_name="stateName"),
                SemanticField(field_name="confidenceLabel"),
            ],
        ),
    )

    semantic_search = SemanticSearch(configurations=[semantic_config])

    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        semantic_search=semantic_search,
    )

    result = index_client.create_or_update_index(index)
    print(f"Created/updated index: {result.name}")
    return result


def create_data_source(indexer_client: SearchIndexerClient):
    """Create a Cosmos DB data source using managed identity."""
    # Managed identity connection string for Cosmos DB
    # IdentityAuthType=AccessToken is required when local auth is disabled on Cosmos DB
    connection_string = f"ResourceId={COSMOSDB_RESOURCE_ID};Database={COSMOSDB_DATABASE};IdentityAuthType=AccessToken;"

    data_source = SearchIndexerDataSourceConnection(
        name=DATA_SOURCE_NAME,
        type="cosmosdb",
        connection_string=connection_string,
        container=SearchIndexerDataContainer(
            name=COSMOSDB_CONTAINER,
            query=INDEXER_QUERY if INDEXER_QUERY else None,
        ),
    )

    result = indexer_client.create_or_update_data_source_connection(data_source)
    print(f"Created/updated data source: {result.name}")
    print(f"  Type: cosmosdb")
    print(f"  Database: {COSMOSDB_DATABASE}")
    print(f"  Container: {COSMOSDB_CONTAINER}")
    if INDEXER_QUERY:
        print(f"  Query filter: {INDEXER_QUERY}")
    return result


def create_indexer(indexer_client: SearchIndexerClient):
    """Create an indexer with daily schedule at 8 AM PST (4 PM UTC)."""
    indexer = SearchIndexer(
        name=INDEXER_NAME,
        data_source_name=DATA_SOURCE_NAME,
        target_index_name=INDEX_NAME,
        schedule=IndexingSchedule(
            interval=_global_search["schedule"]["interval"],
            start_time=_global_search["schedule"]["start_time"],
        ),
        field_mappings=[
            FieldMapping(
                source_field_name="id",
                target_field_name="id",
            ),
            FieldMapping(
                source_field_name="fileName",
                target_field_name="fileName",
            ),
            FieldMapping(
                source_field_name="stateName",
                target_field_name="stateName",
            ),
        ],
    )

    result = indexer_client.create_or_update_indexer(indexer)
    print(f"Created/updated indexer: {result.name}")
    print(f"  Schedule: Daily at 8:00 AM PST (16:00 UTC)")
    print(f"  Data source: {DATA_SOURCE_NAME}")
    print(f"  Target index: {INDEX_NAME}")
    return result


def main():
    use_case = config.get_use_case()
    if not config.is_cosmosdb_use_case():
        print(f"Use case '{use_case}' is not a Cosmos DB use case.")
        print("Set USE_CASE to 'tax_pdf_forms' or 'eng_design_ppt'.")
        sys.exit(1)

    print(f"Use case: {use_case}")
    print(f"Connecting to Azure AI Search: {SEARCH_ENDPOINT}")
    credential = DefaultAzureCredential()

    index_client = SearchIndexClient(
        endpoint=SEARCH_ENDPOINT, credential=credential
    )
    indexer_client = SearchIndexerClient(
        endpoint=SEARCH_ENDPOINT, credential=credential
    )

    print("\n--- Creating Search Index ---")
    create_index(index_client)

    print("\n--- Creating Cosmos DB Data Source Connection ---")
    create_data_source(indexer_client)

    print("\n--- Creating Indexer with Daily Schedule ---")
    create_indexer(indexer_client)

    # Run the indexer immediately for initial population
    print("\n--- Running Indexer (initial population) ---")
    indexer_client.run_indexer(INDEXER_NAME)
    print(f"Indexer '{INDEXER_NAME}' started. Initial indexing in progress...")
    print("The indexer will also run automatically every day at 8:00 AM PST.")

    print("\nDone! AI Search index setup complete for Cosmos DB data source.")


if __name__ == "__main__":
    main()
