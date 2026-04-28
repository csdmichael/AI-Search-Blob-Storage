"""Debug: check what the search index returns for FD-TC-0003 queries."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

cred = DefaultAzureCredential()
sc = SearchClient(
    endpoint=config.search_endpoint(),
    index_name='filter-design-chunked-index',
    credential=cred,
)

# Test 1: Semantic search for Q factor of FD-TC-0003
print("=== SEMANTIC SEARCH: Q factor FD-TC-0003 ===")
for r in sc.search(
    search_text="Q factor FD-TC-0003",
    query_type="semantic",
    semantic_configuration_name="fd-chunked-semantic-config",
    top=5,
    select="id,document_number,section_name,content",
):
    print(f"  doc={r['document_number']}  section={r['section_name']}")
    print(f"  content: {r['content'][:400]}")
    print()

# Test 2: Filter on document_number directly
print("=== FILTERED: document_number eq FD-TC-0003, all sections ===")
for r in sc.search(
    search_text="*",
    filter="document_number eq 'FD-TC-0003'",
    top=15,
    select="id,document_number,section_name,content",
):
    print(f"  section={r['section_name']}")
    print(f"  content: {r['content'][:400]}")
    print()

# Test 3: What does the agent actually get with semantic search + "insertion loss FD-TC-0003"
print("=== SEMANTIC SEARCH: insertion loss FD-TC-0003 ===")
for r in sc.search(
    search_text="what is the insertion loss for FD-TC-0003",
    query_type="semantic",
    semantic_configuration_name="fd-chunked-semantic-config",
    top=5,
    select="id,document_number,section_name,content",
):
    print(f"  doc={r['document_number']}  section={r['section_name']}")
    print(f"  content: {r['content'][:400]}")
    print()
