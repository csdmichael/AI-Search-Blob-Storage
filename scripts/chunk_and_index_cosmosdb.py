"""
Chunk Cosmos DB documents by section for improved AI Search accuracy.

This script reads documents from Azure Cosmos DB (taxform container),
filters by file type (PDF for tax forms, PPT for engineering design),
and creates a chunked search index with:
- Section-level chunking for granular search results
- Custom scoring profiles to boost title and category fields
- Semantic configuration for natural language queries
- Metadata preservation for source traceability

Set USE_CASE env var to select: tax_pdf_forms or eng_design_ppt
"""

import os
import sys
import hashlib
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient
from azure.search.documents import SearchIndexingBufferedSender
from azure.search.documents.indexes import SearchIndexClient
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
    ScoringProfile,
    TextWeights,
)

_uc_search = config.uc_search_config()
_global_search = config.search_config()
_doc_cfg = config.uc_document_config()
_cosmosdb = config.cosmosdb_config()

SEARCH_ENDPOINT = config.search_endpoint()
INDEX_NAME = _uc_search["chunked_index"]["name"]
SEMANTIC_CONFIG_NAME = _uc_search["chunked_index"]["semantic_config_name"]
SCORING_PROFILE_NAME = _uc_search["chunked_index"]["scoring_profile_name"]

MAX_CHUNK_SIZE = _global_search["chunking"]["max_chunk_size"]
OVERLAP_SIZE = _global_search["chunking"]["overlap_size"]
DOC_PREFIX = _doc_cfg["document_prefix"]
FILE_FILTER = _doc_cfg.get("cosmosdb_filter", "")

COSMOSDB_DATABASE = _cosmosdb["database_name"]
COSMOSDB_CONTAINER = _cosmosdb["container_name"]
COSMOSDB_ACCOUNT_NAME = _cosmosdb["account_name"]

USE_CASE = config.get_use_case()


def create_chunked_index(index_client: SearchIndexClient):
    """Create the chunked index with scoring profile and semantic config."""

    if USE_CASE == "tax_pdf_forms":
        extra_fields = [
            SearchableField(name="state", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="stateName", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="overallConfidence", type=SearchFieldDataType.Double, filterable=True, sortable=True),
            SimpleField(name="confidenceCategory", type=SearchFieldDataType.String, filterable=True, facetable=True),
        ]
        scoring_weights = {
            "title": 3.0,
            "stateName": 2.5,
            "section_name": 2.0,
            "content": 1.0,
        }
        keyword_fields = [
            SemanticField(field_name="stateName"),
            SemanticField(field_name="section_name"),
        ]
    else:  # eng_design_ppt
        extra_fields = [
            SearchableField(name="state", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="stateName", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="overallConfidence", type=SearchFieldDataType.Double, filterable=True, sortable=True),
            SimpleField(name="confidenceCategory", type=SearchFieldDataType.String, filterable=True, facetable=True),
        ]
        scoring_weights = {
            "title": 3.0,
            "section_name": 2.0,
            "content": 1.0,
            "stateName": 2.0,
        }
        keyword_fields = [
            SemanticField(field_name="stateName"),
            SemanticField(field_name="section_name"),
        ]

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
        SearchableField(name="title", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SearchableField(name="section_name", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="document_number", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SimpleField(name="source_file", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="file_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="status", type=SearchFieldDataType.String, filterable=True),
    ] + extra_fields

    scoring_profile = ScoringProfile(
        name=SCORING_PROFILE_NAME,
        text_weights=TextWeights(weights=scoring_weights),
    )

    semantic_config = SemanticConfiguration(
        name=SEMANTIC_CONFIG_NAME,
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="content")],
            title_field=SemanticField(field_name="title"),
            keywords_fields=keyword_fields,
        ),
    )

    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        scoring_profiles=[scoring_profile],
        default_scoring_profile=SCORING_PROFILE_NAME,
        semantic_search=SemanticSearch(configurations=[semantic_config]),
    )

    result = index_client.create_or_update_index(index)
    print(f"Created/updated chunked index: {result.name}")
    print(f"  Scoring profile: {SCORING_PROFILE_NAME}")
    print(f"  Semantic config: {SEMANTIC_CONFIG_NAME}")
    return result


def fetch_documents_from_cosmosdb(credential) -> list[dict]:
    """Fetch documents from Cosmos DB, filtering by file type."""
    cosmosdb_endpoint = f"https://{COSMOSDB_ACCOUNT_NAME}.documents.azure.com:443/"
    client = CosmosClient(cosmosdb_endpoint, credential=credential)
    database = client.get_database_client(COSMOSDB_DATABASE)
    container = database.get_container_client(COSMOSDB_CONTAINER)

    # Query with filter for the appropriate file type
    if FILE_FILTER:
        query = f"SELECT * FROM c WHERE CONTAINS(LOWER(c.fileName), '.{FILE_FILTER}')"
        print(f"  Querying Cosmos DB with filter: .{FILE_FILTER} files")
    else:
        query = "SELECT * FROM c"
        print("  Querying all documents from Cosmos DB")

    documents = list(container.query_items(query=query, enable_cross_partition_query=True))
    print(f"  Fetched {len(documents)} documents from Cosmos DB")
    return documents


def chunk_cosmosdb_document(doc: dict) -> list[dict]:
    """Split a Cosmos DB document into section-level chunks with metadata.

    The actual Cosmos DB documents have this structure:
    - fileName, state, stateName, status, overallConfidence, confidenceCategory
    - sections: [{sectionName, sectionIndex, fields: [{fieldName, extractedValue, ...}]}]
    """
    doc_id = doc.get("id", "")
    file_name = doc.get("fileName", "")
    state = doc.get("state", "")
    state_name = doc.get("stateName", "")
    status = doc.get("status", "")
    overall_confidence = doc.get("overallConfidence", 0.0)
    confidence_category = doc.get("confidenceCategory", "")
    sections = doc.get("sections", [])

    if not sections:
        return []

    # Common metadata for all chunks from this document
    common_meta = {
        "state": state,
        "stateName": state_name,
        "overallConfidence": overall_confidence,
        "confidenceCategory": confidence_category,
    }

    chunks = []

    # Chunk 0: Full-document summary for cross-section queries
    summary_lines = [f"=== {file_name} — COMPLETE DOCUMENT SUMMARY ==="]
    summary_lines.append(f"State: {state_name} ({state})")
    summary_lines.append(f"Status: {status}")
    summary_lines.append(f"Overall Confidence: {overall_confidence} ({confidence_category})")
    summary_lines.append("")
    for section in sections:
        sec_name = section.get("sectionName", "Unknown")
        summary_lines.append(f"--- {sec_name} ---")
        for field in section.get("fields", []):
            fn = field.get("fieldName", "")
            val = field.get("correctedValue") or field.get("extractedValue", "")
            if fn and val:
                summary_lines.append(f"  {fn}: {val}")
    summary_text = "\n".join(summary_lines)
    if len(summary_text) <= MAX_CHUNK_SIZE:
        chunk_id = hashlib.md5(f"{doc_id}:summary".encode()).hexdigest()
        summary_chunk = {
            "id": chunk_id,
            "content": f"Document: {file_name} | State: {state_name}\n\n{summary_text}",
            "title": file_name,
            "section_name": "Full Document Summary",
            "document_number": doc_id,
            "source_file": file_name,
            "file_type": os.path.splitext(file_name)[1].lstrip(".").lower() or "pdf",
            "category": state_name,
            "status": status,
        }
        summary_chunk.update(common_meta)
        chunks.append(summary_chunk)

    # Per-section chunks
    for section in sections:
        section_name = section.get("sectionName", "Unknown Section")
        fields = section.get("fields", [])

        if not fields:
            continue

        # Flatten fields into readable text content
        field_lines = []
        for field in fields:
            field_name = field.get("fieldName", "")
            extracted = field.get("extractedValue", "")
            corrected = field.get("correctedValue")
            value = corrected if corrected else extracted
            if field_name and value:
                field_lines.append(f"{field_name}: {value}")

        if not field_lines:
            continue

        section_text = "\n".join(field_lines)
        context_prefix = f"Document: {file_name} | State: {state_name}\nSection: {section_name}\n\n"

        sub_chunks = _split_large_text(section_text, MAX_CHUNK_SIZE - len(context_prefix))

        for j, sub_text in enumerate(sub_chunks):
            suffix = f":part{j+1}" if len(sub_chunks) > 1 else ""
            chunk_id = hashlib.md5(f"{doc_id}:{section_name}{suffix}".encode()).hexdigest()

            chunk = {
                "id": chunk_id,
                "content": context_prefix + sub_text,
                "title": file_name,
                "section_name": section_name,
                "document_number": doc_id,
                "source_file": file_name,
                "file_type": os.path.splitext(file_name)[1].lstrip(".").lower() or "pdf",
                "category": state_name,
                "status": status,
            }
            chunk.update(common_meta)
            chunks.append(chunk)

    # If no section chunks were created, create a single chunk from all fields
    if not chunks:
        all_fields_text = []
        for section in sections:
            for field in section.get("fields", []):
                fn = field.get("fieldName", "")
                val = field.get("correctedValue") or field.get("extractedValue", "")
                if fn and val:
                    all_fields_text.append(f"{fn}: {val}")

        if all_fields_text:
            chunk_id = hashlib.md5(f"{doc_id}:full".encode()).hexdigest()
            chunk = {
                "id": chunk_id,
                "content": f"Document: {file_name} | State: {state_name}\n\n" + "\n".join(all_fields_text),
                "title": file_name,
                "section_name": "Full Document",
                "document_number": doc_id,
                "source_file": file_name,
                "file_type": os.path.splitext(file_name)[1].lstrip(".").lower() or "pdf",
                "category": state_name,
                "status": status,
            }
            chunk.update(common_meta)
            chunks.append(chunk)

    return chunks


def _split_large_text(text: str, max_size: int) -> list[str]:
    """Split text into sub-chunks with overlap, breaking at line boundaries."""
    if len(text) <= max_size:
        return [text]

    parts = []
    lines = text.split("\n")
    current = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1
        if current_len + line_len > max_size and current:
            parts.append("\n".join(current))
            overlap_lines = []
            overlap_len = 0
            for ol in reversed(current):
                if overlap_len + len(ol) + 1 > OVERLAP_SIZE:
                    break
                overlap_lines.insert(0, ol)
                overlap_len += len(ol) + 1
            current = overlap_lines
            current_len = overlap_len
        current.append(line)
        current_len += line_len

    if current:
        parts.append("\n".join(current))

    return parts


def main():
    use_case = config.get_use_case()
    if not config.is_cosmosdb_use_case():
        print(f"Use case '{use_case}' is not a Cosmos DB use case.")
        print("Set USE_CASE to 'tax_pdf_forms' or 'eng_design_ppt'.")
        sys.exit(1)

    print(f"Use case: {use_case}")
    print(f"Cosmos DB: {COSMOSDB_ACCOUNT_NAME} / {COSMOSDB_DATABASE} / {COSMOSDB_CONTAINER}")
    print(f"File filter: .{FILE_FILTER}")
    print(f"Target index: {INDEX_NAME}")

    credential = DefaultAzureCredential()

    # Step 1: Create chunked index
    print("\n--- Creating Chunked Index ---")
    index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=credential)
    create_chunked_index(index_client)

    # Step 2: Fetch documents from Cosmos DB
    print("\n--- Fetching Documents from Cosmos DB ---")
    documents = fetch_documents_from_cosmosdb(credential)

    if not documents:
        print("No documents found matching the filter. Exiting.")
        return

    # Step 3: Chunk documents
    print("\n--- Chunking Documents ---")
    all_chunks = []
    for doc in documents:
        chunks = chunk_cosmosdb_document(doc)
        all_chunks.extend(chunks)
        if chunks:
            print(f"  {doc.get('file_name', doc.get('id', '?'))}: {len(chunks)} chunks")

    print(f"\nTotal chunks: {len(all_chunks)}")

    # Step 4: Upload chunks to AI Search
    print("\n--- Uploading Chunks to AI Search ---")
    with SearchIndexingBufferedSender(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=credential,
    ) as batch_client:
        batch_client.upload_documents(all_chunks)

    print(f"\nDone! {len(all_chunks)} chunks uploaded to index '{INDEX_NAME}'.")


if __name__ == "__main__":
    main()
