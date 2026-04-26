"""
Chunk engineering documents by section for improved AI Search accuracy.

Best Practices Implemented:
- Section-level chunking: Each document section becomes its own search chunk
- Metadata preservation: Each chunk retains parent document metadata for traceability
- Overlap context: Section headers and document context are preserved in each chunk
- Consistent chunk sizing: Sections are further split if they exceed max_chunk_size
- Deduplication: Chunk IDs are deterministic (doc_number + section) to avoid duplicates
"""

import os
import re
import json
import hashlib
from azure.identity import DefaultAzureCredential
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
import config

config.validate_required(["SEARCH_SERVICE_NAME"])

SEARCH_ENDPOINT = config.SEARCH_ENDPOINT
INDEX_NAME = config.SEARCH_CHUNKED_INDEX_NAME
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Chunking configuration
MAX_CHUNK_SIZE = 2000  # characters per chunk
OVERLAP_SIZE = 200     # overlap between sub-chunks of large sections


# ─────────────────────────────────────────────────────────────────────
# Section-based chunking
# ─────────────────────────────────────────────────────────────────────

SECTION_PATTERN = re.compile(
    r"^─{20,}\n(\d+\.\s+[A-Z\s\(\)]+)\n─{20,}$",
    re.MULTILINE,
)

HEADER_PATTERN = re.compile(
    r"^Document Number:\s*(.+)$", re.MULTILINE
)
TITLE_PATTERN = re.compile(
    r"^Title:\s*(.+)$", re.MULTILINE
)
STATUS_PATTERN = re.compile(
    r"^Status:\s*(.+)$", re.MULTILINE
)
PRODUCT_PATTERN = re.compile(
    r"^- Product Line:\s*(.+)$", re.MULTILINE
)
DEFECT_PATTERN = re.compile(
    r"^- Target Defect:\s*(.+)$", re.MULTILINE
)
PROCESS_PATTERN = re.compile(
    r"^- Process Step:\s*(.+)$", re.MULTILINE
)
TECHNODE_PATTERN = re.compile(
    r"^- Technology Node:\s*(.+)$", re.MULTILINE
)
FAB_PATTERN = re.compile(
    r"^Fab Location:\s*(.+)$", re.MULTILINE
)


def extract_metadata(content: str) -> dict:
    """Extract structured metadata from a document."""
    def _match(pattern):
        m = pattern.search(content)
        return m.group(1).strip() if m else ""

    return {
        "document_number": _match(HEADER_PATTERN),
        "title": _match(TITLE_PATTERN),
        "status": _match(STATUS_PATTERN),
        "product_line": _match(PRODUCT_PATTERN),
        "target_defect": _match(DEFECT_PATTERN),
        "process_step": _match(PROCESS_PATTERN),
        "technology_node": _match(TECHNODE_PATTERN),
        "fab_location": _match(FAB_PATTERN),
    }


def chunk_document(content: str, filename: str) -> list[dict]:
    """Split a document into section-level chunks with metadata."""
    metadata = extract_metadata(content)
    doc_number = metadata["document_number"] or filename.replace(".txt", "")

    # Find all section boundaries
    section_matches = list(SECTION_PATTERN.finditer(content))

    if not section_matches:
        # No sections found — index as a single chunk
        chunk_id = hashlib.md5(f"{doc_number}:full".encode()).hexdigest()
        return [{
            "id": chunk_id,
            "content": content[:MAX_CHUNK_SIZE * 3],
            "section_name": "Full Document",
            "document_number": doc_number,
            "title": metadata["title"],
            "status": metadata["status"],
            "product_line": metadata["product_line"],
            "target_defect": metadata["target_defect"],
            "process_step": metadata["process_step"],
            "technology_node": metadata["technology_node"],
            "fab_location": metadata["fab_location"],
            "source_file": filename,
        }]

    chunks = []

    # Extract the header/metadata section (before first numbered section)
    header_end = section_matches[0].start()
    header_text = content[:header_end].strip()
    if header_text:
        chunk_id = hashlib.md5(f"{doc_number}:header".encode()).hexdigest()
        chunks.append({
            "id": chunk_id,
            "content": header_text,
            "section_name": "Document Header",
            "document_number": doc_number,
            "title": metadata["title"],
            "status": metadata["status"],
            "product_line": metadata["product_line"],
            "target_defect": metadata["target_defect"],
            "process_step": metadata["process_step"],
            "technology_node": metadata["technology_node"],
            "fab_location": metadata["fab_location"],
            "source_file": filename,
        })

    # Extract each numbered section
    for i, match in enumerate(section_matches):
        section_name = match.group(1).strip()
        section_start = match.end()
        section_end = (
            section_matches[i + 1].start()
            if i + 1 < len(section_matches)
            else len(content)
        )
        section_text = content[section_start:section_end].strip()

        # Remove trailing document footer markers
        section_text = re.sub(r"={20,}\nEND OF DOCUMENT.*$", "", section_text, flags=re.DOTALL).strip()

        if not section_text:
            continue

        # Context prefix for every chunk: document identity + section name
        context_prefix = (
            f"Document: {doc_number} | {metadata['title']}\n"
            f"Section: {section_name}\n\n"
        )

        # Sub-chunk if the section is too large
        sub_chunks = _split_large_text(section_text, MAX_CHUNK_SIZE - len(context_prefix))

        for j, sub_text in enumerate(sub_chunks):
            suffix = f":part{j+1}" if len(sub_chunks) > 1 else ""
            chunk_id = hashlib.md5(
                f"{doc_number}:{section_name}{suffix}".encode()
            ).hexdigest()

            chunks.append({
                "id": chunk_id,
                "content": context_prefix + sub_text,
                "section_name": section_name,
                "document_number": doc_number,
                "title": metadata["title"],
                "status": metadata["status"],
                "product_line": metadata["product_line"],
                "target_defect": metadata["target_defect"],
                "process_step": metadata["process_step"],
                "technology_node": metadata["technology_node"],
                "fab_location": metadata["fab_location"],
                "source_file": filename,
            })

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
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > max_size and current:
            parts.append("\n".join(current))
            # Keep last few lines as overlap
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


# ─────────────────────────────────────────────────────────────────────
# Enhanced index with chunk-level fields and scoring
# ─────────────────────────────────────────────────────────────────────

def create_chunked_index(index_client: SearchIndexClient):
    """Create an enhanced search index optimized for chunked documents."""
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
        SearchableField(name="section_name", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="document_number", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
        SimpleField(name="status", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="product_line", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="target_defect", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="process_step", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="technology_node", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="fab_location", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="source_file", type=SearchFieldDataType.String, filterable=True),
    ]

    # Semantic configuration: prioritize content and title
    semantic_config = SemanticConfiguration(
        name="chunked-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="content")],
            title_field=SemanticField(field_name="title"),
            keywords_fields=[
                SemanticField(field_name="document_number"),
                SemanticField(field_name="section_name"),
            ],
        ),
    )

    # Scoring profile: boost title and section matches
    scoring_profile = ScoringProfile(
        name="boost-title-section",
        text_weights=TextWeights(
            weights={
                "title": 3.0,
                "section_name": 2.0,
                "content": 1.0,
                "document_number": 2.5,
            }
        ),
    )

    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        semantic_search=SemanticSearch(configurations=[semantic_config]),
        scoring_profiles=[scoring_profile],
        default_scoring_profile="boost-title-section",
    )

    result = index_client.create_or_update_index(index)
    print(f"Created/updated chunked index: {result.name}")
    return result


def upload_chunks(credential, chunks: list[dict]):
    """Upload chunks using SearchIndexingBufferedSender for efficient batching."""
    print(f"\nUploading {len(chunks)} chunks to index '{INDEX_NAME}'...")

    with SearchIndexingBufferedSender(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=credential,
    ) as sender:
        sender.upload_documents(chunks)

    print(f"Successfully uploaded {len(chunks)} chunks.")


def main():
    credential = DefaultAzureCredential()
    index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=credential)

    # Step 1: Create the enhanced chunked index
    print("--- Creating Chunked Search Index ---")
    create_chunked_index(index_client)

    # Step 2: Read and chunk all documents
    if not os.path.exists(DATA_DIR):
        print(f"Error: Data directory not found: {DATA_DIR}")
        print("Run generate_docs.py first.")
        return

    files = sorted(f for f in os.listdir(DATA_DIR) if f.startswith("KLA-MFG-TC-") and f.endswith(".txt"))
    print(f"\nChunking {len(files)} documents...")

    all_chunks = []
    for filename in files:
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        chunks = chunk_document(content, filename)
        all_chunks.extend(chunks)
        print(f"  {filename} → {len(chunks)} chunks")

    print(f"\nTotal chunks: {len(all_chunks)}")

    # Step 3: Upload chunks
    upload_chunks(credential, all_chunks)

    # Step 4: Summary statistics
    sections = {}
    for c in all_chunks:
        s = c["section_name"]
        sections[s] = sections.get(s, 0) + 1

    print("\n--- Chunk Distribution by Section ---")
    for section, count in sorted(sections.items(), key=lambda x: -x[1]):
        print(f"  {section}: {count} chunks")

    print(f"\nDone! Chunked index '{INDEX_NAME}' is ready for search.")
    print("Use semantic_configuration_name='chunked-semantic-config' for semantic queries.")


if __name__ == "__main__":
    main()
