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
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

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

_uc_search = config.uc_search_config()
_global_search = config.search_config()
_doc_cfg = config.uc_document_config()

SEARCH_ENDPOINT = config.search_endpoint()
INDEX_NAME = _uc_search["chunked_index"]["name"]
SEMANTIC_CONFIG_NAME = _uc_search["chunked_index"]["semantic_config_name"]
SCORING_PROFILE_NAME = _uc_search["chunked_index"]["scoring_profile_name"]
DATA_DIR = config.uc_data_dir()

# Chunking configuration
MAX_CHUNK_SIZE = _global_search["chunking"]["max_chunk_size"]
OVERLAP_SIZE = _global_search["chunking"]["overlap_size"]
DOC_PREFIX = _doc_cfg["document_prefix"]
FILE_FORMAT = _doc_cfg["file_format"]


def _read_file_text(filepath: str) -> str:
    """Read text content from a .txt or .pdf file."""
    if filepath.lower().endswith(".pdf"):
        try:
            from fpdf import FPDF  # noqa: F401 — just to verify fpdf2 is installed
            import subprocess
            # Use a simple PDF-to-text approach: read raw bytes and extract text objects
            # For production, use a proper PDF parser; here we use the built-in pdfminer or fallback
        except ImportError:
            pass
        # Try PyPDF2 / pypdf first, then fallback to raw extraction
        try:
            from pypdf import PdfReader
            reader = PdfReader(filepath)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if text.strip():
                return text
        except ImportError:
            pass
        # Fallback: read the binary and try basic text extraction
        import struct
        with open(filepath, "rb") as f:
            raw = f.read()
        # Extract text between BT and ET markers (basic PDF text extraction)
        text_parts = []
        for match in re.finditer(rb"\(([^)]+)\)", raw):
            try:
                text_parts.append(match.group(1).decode("latin-1"))
            except Exception:
                pass
        return "\n".join(text_parts) if text_parts else ""
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()


# ─────────────────────────────────────────────────────────────────────
# Section-based chunking
# ─────────────────────────────────────────────────────────────────────

# Pattern for .txt documents (sections separated by ─ lines)
SECTION_PATTERN_TXT = re.compile(
    r"^─{20,}\n(\d+\.\s+[A-Z\s\(\)]+)\n─{20,}$",
    re.MULTILINE,
)

# Pattern for PDF-extracted text (section headers on own line, e.g. "1. OBJECTIVE")
SECTION_PATTERN_PDF = re.compile(
    r"^(\d+\.\s+[A-Z\s\(\)&]+)$",
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

# ── Engineering docs metadata patterns ─────────────────────────────
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

# ── Filter design metadata patterns ────────────────────────────────
FILTER_TYPE_PATTERN = re.compile(
    r"^- Filter Type:\s*(.+)$", re.MULTILINE
)
FREQ_BAND_PATTERN = re.compile(
    r"^- Frequency Band:\s*(.+)$", re.MULTILINE
)
SUBSTRATE_PATTERN = re.compile(
    r"^- Substrate:\s*(.+)$", re.MULTILINE
)
APPLICATION_PATTERN = re.compile(
    r"^- Application:\s*(.+)$", re.MULTILINE
)
DESIGN_CENTER_PATTERN = re.compile(
    r"^Design Center:\s*(.+)$", re.MULTILINE
)
PACKAGE_PATTERN = re.compile(
    r"^- Package:\s*(.+)$", re.MULTILINE
)

USE_CASE = config.get_use_case()


def extract_metadata(content: str) -> dict:
    """Extract structured metadata from a document, use-case-aware."""
    def _match(pattern):
        m = pattern.search(content)
        return m.group(1).strip() if m else ""

    common = {
        "document_number": _match(HEADER_PATTERN),
        "title": _match(TITLE_PATTERN),
        "status": _match(STATUS_PATTERN),
    }

    if USE_CASE == "filter_design":
        common.update({
            "filter_type": _match(FILTER_TYPE_PATTERN),
            "frequency_band": _match(FREQ_BAND_PATTERN),
            "substrate_material": _match(SUBSTRATE_PATTERN),
            "application": _match(APPLICATION_PATTERN),
            "design_center": _match(DESIGN_CENTER_PATTERN),
            "package_type": _match(PACKAGE_PATTERN),
        })
    else:
        common.update({
            "product_line": _match(PRODUCT_PATTERN),
            "target_defect": _match(DEFECT_PATTERN),
            "process_step": _match(PROCESS_PATTERN),
            "technology_node": _match(TECHNODE_PATTERN),
            "fab_location": _match(FAB_PATTERN),
        })

    return common


def _metadata_fields_for_chunk(metadata: dict, filename: str) -> dict:
    """Build the metadata portion of a chunk dict from extracted metadata."""
    base = {
        "document_number": metadata["document_number"],
        "title": metadata["title"],
        "status": metadata["status"],
        "source_file": filename,
    }
    if USE_CASE == "filter_design":
        base.update({
            "filter_type": metadata.get("filter_type", ""),
            "frequency_band": metadata.get("frequency_band", ""),
            "substrate_material": metadata.get("substrate_material", ""),
            "application": metadata.get("application", ""),
            "design_center": metadata.get("design_center", ""),
            "package_type": metadata.get("package_type", ""),
        })
    else:
        base.update({
            "product_line": metadata.get("product_line", ""),
            "target_defect": metadata.get("target_defect", ""),
            "process_step": metadata.get("process_step", ""),
            "technology_node": metadata.get("technology_node", ""),
            "fab_location": metadata.get("fab_location", ""),
        })
    return base


def chunk_document(content: str, filename: str) -> list[dict]:
    """Split a document into section-level chunks with metadata."""
    metadata = extract_metadata(content)
    doc_number = metadata["document_number"] or filename.replace(".txt", "").replace(".pdf", "")

    # Find all section boundaries — try TXT pattern first, then PDF pattern
    section_matches = list(SECTION_PATTERN_TXT.finditer(content))
    if not section_matches:
        section_matches = list(SECTION_PATTERN_PDF.finditer(content))

    if not section_matches:
        # No sections found — index as a single chunk
        chunk_id = hashlib.md5(f"{doc_number}:full".encode()).hexdigest()
        chunk = {
            "id": chunk_id,
            "content": content[:MAX_CHUNK_SIZE * 3],
            "section_name": "Full Document",
        }
        chunk.update(_metadata_fields_for_chunk(metadata, filename))
        return [chunk]

    chunks = []

    # Extract the header/metadata section (before first numbered section)
    header_end = section_matches[0].start()
    header_text = content[:header_end].strip()
    if header_text:
        chunk_id = hashlib.md5(f"{doc_number}:header".encode()).hexdigest()
        chunk = {
            "id": chunk_id,
            "content": header_text,
            "section_name": "Document Header",
        }
        chunk.update(_metadata_fields_for_chunk(metadata, filename))
        chunks.append(chunk)

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

            chunk = {
                "id": chunk_id,
                "content": context_prefix + sub_text,
                "section_name": section_name,
            }
            chunk.update(_metadata_fields_for_chunk(metadata, filename))
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
    """Create an enhanced search index optimized for chunked documents.

    Engineering docs fields: product_line, target_defect, process_step, technology_node, fab_location
    Filter design fields:   filter_type, frequency_band, substrate_material, application, design_center, package_type
    """
    # Common fields
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
        SearchableField(name="section_name", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="document_number", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
        SimpleField(name="status", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="source_file", type=SearchFieldDataType.String, filterable=True),
    ]

    # Use-case-specific metadata fields
    if USE_CASE == "filter_design":
        fields.extend([
            SimpleField(name="filter_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="frequency_band", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="substrate_material", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="application", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="design_center", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="package_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
        ])
    else:
        fields.extend([
            SimpleField(name="product_line", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="target_defect", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="process_step", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="technology_node", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="fab_location", type=SearchFieldDataType.String, filterable=True, facetable=True),
        ])

    # Semantic configuration: prioritize content and title
    semantic_config = SemanticConfiguration(
        name=SEMANTIC_CONFIG_NAME,
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
        name=SCORING_PROFILE_NAME,
        text_weights=TextWeights(
            weights=_global_search["scoring_weights"]
        ),
    )

    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        semantic_search=SemanticSearch(configurations=[semantic_config]),
        scoring_profiles=[scoring_profile],
        default_scoring_profile=SCORING_PROFILE_NAME,
    )

    # Delete existing index if schema has changed (fields cannot be removed in-place)
    try:
        index_client.delete_index(INDEX_NAME)
        print(f"Deleted existing index '{INDEX_NAME}' (schema update required)")
    except Exception:
        pass  # Index doesn't exist yet — fine

    result = index_client.create_or_update_index(index)
    print(f"Created chunked index: {result.name}")
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

    file_ext = f".{FILE_FORMAT}"
    files = sorted(f for f in os.listdir(DATA_DIR) if f.startswith(DOC_PREFIX) and f.endswith(file_ext))
    print(f"\nChunking {len(files)} documents...")

    all_chunks = []
    for filename in files:
        filepath = os.path.join(DATA_DIR, filename)
        content = _read_file_text(filepath)
        chunks = chunk_document(content, filename)
        all_chunks.extend(chunks)
        print(f"  {filename} -> {len(chunks)} chunks")

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
