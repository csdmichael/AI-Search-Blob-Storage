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
            SearchableField(name="form_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="jurisdiction", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="exemption_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="filing_deadline", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="effective_date", type=SearchFieldDataType.String, filterable=True),
        ]
        scoring_weights = {
            "title": 3.0,
            "form_type": 2.5,
            "section_name": 2.0,
            "content": 1.0,
            "jurisdiction": 2.0,
        }
        keyword_fields = [
            SemanticField(field_name="form_type"),
            SemanticField(field_name="jurisdiction"),
        ]
    else:  # eng_design_ppt
        extra_fields = [
            SearchableField(name="design_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="project_name", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="author", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="revision", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="slide_count", type=SearchFieldDataType.Int32, filterable=True),
        ]
        scoring_weights = {
            "title": 3.0,
            "design_type": 2.5,
            "section_name": 2.0,
            "content": 1.0,
            "project_name": 2.0,
        }
        keyword_fields = [
            SemanticField(field_name="design_type"),
            SemanticField(field_name="project_name"),
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
        query = f"SELECT * FROM c WHERE CONTAINS(LOWER(c.file_name), '.{FILE_FILTER}')"
        print(f"  Querying Cosmos DB with filter: .{FILE_FILTER} files")
    else:
        query = "SELECT * FROM c"
        print("  Querying all documents from Cosmos DB")

    documents = list(container.query_items(query=query, enable_cross_partition_query=True))
    print(f"  Fetched {len(documents)} documents from Cosmos DB")
    return documents


def chunk_cosmosdb_document(doc: dict) -> list[dict]:
    """Split a Cosmos DB document into section-level chunks with metadata."""
    doc_id = doc.get("id", "")
    file_name = doc.get("file_name", "")
    title = doc.get("title", file_name)
    content = doc.get("content", "")
    category = doc.get("category", "")
    status = doc.get("status", "")
    file_type = doc.get("file_type", FILE_FILTER)

    if not content:
        return []

    # Extract use-case-specific metadata
    if USE_CASE == "tax_pdf_forms":
        extra_meta = {
            "form_type": doc.get("form_type", ""),
            "jurisdiction": doc.get("jurisdiction", ""),
            "exemption_type": doc.get("exemption_type", ""),
            "filing_deadline": doc.get("filing_deadline", ""),
            "effective_date": doc.get("effective_date", ""),
        }
    else:
        extra_meta = {
            "design_type": doc.get("design_type", ""),
            "project_name": doc.get("project_name", ""),
            "author": doc.get("author", ""),
            "revision": doc.get("revision", ""),
            "slide_count": doc.get("slide_count", 0),
        }

    # Try to split by sections (look for numbered headers or slide titles)
    sections = _extract_sections(content)

    if not sections:
        # No sections found — index as a single chunk
        chunk_id = hashlib.md5(f"{doc_id}:full".encode()).hexdigest()
        chunk = {
            "id": chunk_id,
            "content": content[:MAX_CHUNK_SIZE * 3],
            "title": title,
            "section_name": "Full Document",
            "document_number": doc_id,
            "source_file": file_name,
            "file_type": file_type,
            "category": category,
            "status": status,
        }
        chunk.update(extra_meta)
        return [chunk]

    chunks = []
    for section_name, section_text in sections:
        if not section_text.strip():
            continue

        context_prefix = f"Document: {doc_id} | {title}\nSection: {section_name}\n\n"
        sub_chunks = _split_large_text(section_text, MAX_CHUNK_SIZE - len(context_prefix))

        for j, sub_text in enumerate(sub_chunks):
            suffix = f":part{j+1}" if len(sub_chunks) > 1 else ""
            chunk_id = hashlib.md5(f"{doc_id}:{section_name}{suffix}".encode()).hexdigest()

            chunk = {
                "id": chunk_id,
                "content": context_prefix + sub_text,
                "title": title,
                "section_name": section_name,
                "document_number": doc_id,
                "source_file": file_name,
                "file_type": file_type,
                "category": category,
                "status": status,
            }
            chunk.update(extra_meta)
            chunks.append(chunk)

    return chunks


def _extract_sections(content: str) -> list[tuple[str, str]]:
    """Extract named sections from document content.

    Looks for patterns like:
    - '## Section Name' (Markdown headers)
    - 'Slide N: Title' (PowerPoint slides)
    - 'Section N: Title' or 'N. TITLE' (numbered sections)
    """
    import re

    # Try markdown headers
    header_pattern = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)
    # Try slide-style headers
    slide_pattern = re.compile(r"^(?:Slide\s+\d+[:\s]+)(.+)$", re.MULTILINE | re.IGNORECASE)
    # Try numbered section headers
    numbered_pattern = re.compile(r"^(\d+\.?\s+[A-Z][A-Za-z\s&()]+)$", re.MULTILINE)

    for pattern in [header_pattern, slide_pattern, numbered_pattern]:
        matches = list(pattern.finditer(content))
        if len(matches) >= 2:
            sections = []
            for i, match in enumerate(matches):
                section_name = match.group(1).strip()
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
                section_text = content[start:end].strip()
                sections.append((section_name, section_text))
            return sections

    return []


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
