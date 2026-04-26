"""
Create an Azure AI Search index with a blob storage data source, indexer,
and schedule it to refresh daily at 8 AM PST.

Supports both semantic and keyword search.
Uses managed identity for authentication.
"""

import os
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
import config

config.validate_required([
    "SEARCH_SERVICE_NAME",
    "STORAGE_ACCOUNT_NAME",
    "SUBSCRIPTION_ID",
    "RESOURCE_GROUP",
])

SEARCH_ENDPOINT = config.SEARCH_ENDPOINT
INDEX_NAME = config.SEARCH_INDEX_NAME
INDEXER_NAME = config.SEARCH_INDEXER_NAME
DATA_SOURCE_NAME = config.SEARCH_DATA_SOURCE_NAME

STORAGE_ACCOUNT_NAME = config.STORAGE_ACCOUNT_NAME
CONTAINER_NAME = config.STORAGE_CONTAINER_NAME
STORAGE_RESOURCE_ID = config.STORAGE_RESOURCE_ID


def create_index(index_client: SearchIndexClient):
    """Create the search index with semantic configuration."""
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
            name="metadata_storage_name",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="metadata_storage_path",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="metadata_storage_last_modified",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="metadata_storage_size",
            type=SearchFieldDataType.Int64,
            filterable=True,
        ),
        SimpleField(
            name="metadata_content_type",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
    ]

    semantic_config = SemanticConfiguration(
        name="engineering-docs-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="content")],
            title_field=SemanticField(field_name="metadata_storage_name"),
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
    """Create a blob storage data source using managed identity."""
    # Use managed identity resource ID-based connection string
    connection_string = f"ResourceId={STORAGE_RESOURCE_ID};"

    data_source = SearchIndexerDataSourceConnection(
        name=DATA_SOURCE_NAME,
        type="azureblob",
        connection_string=connection_string,
        container=SearchIndexerDataContainer(name=CONTAINER_NAME),
    )

    result = indexer_client.create_or_update_data_source_connection(data_source)
    print(f"Created/updated data source: {result.name}")
    return result


def create_indexer(indexer_client: SearchIndexerClient):
    """Create an indexer with daily schedule at 8 AM PST (4 PM UTC)."""
    # 8 AM PST = 4 PM UTC (PST is UTC-8)
    # ISO 8601 duration: P1D = every 1 day
    # Start time: 16:00 UTC = 8:00 AM PST
    indexer = SearchIndexer(
        name=INDEXER_NAME,
        data_source_name=DATA_SOURCE_NAME,
        target_index_name=INDEX_NAME,
        schedule=IndexingSchedule(
            interval="PT24H",  # Every 24 hours
            start_time="2024-01-01T16:00:00Z",  # 8 AM PST = 4 PM UTC
        ),
        field_mappings=[
            FieldMapping(
                source_field_name="metadata_storage_path",
                target_field_name="id",
                mapping_function={"name": "base64Encode"},
            ),
            FieldMapping(
                source_field_name="metadata_storage_name",
                target_field_name="metadata_storage_name",
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

    print("\n--- Creating Data Source Connection ---")
    create_data_source(indexer_client)

    print("\n--- Creating Indexer with Daily Schedule ---")
    create_indexer(indexer_client)

    # Run the indexer immediately for initial population
    print("\n--- Running Indexer (initial population) ---")
    indexer_client.run_indexer(INDEXER_NAME)
    print(f"Indexer '{INDEXER_NAME}' started. Initial indexing in progress...")
    print("The indexer will also run automatically every day at 8:00 AM PST.")

    print("\nDone! AI Search index setup complete.")


if __name__ == "__main__":
    main()
