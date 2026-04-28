"""
Test the AI Search index with semantic and keyword search queries,
and test the Foundry agent with sample prompts.

Set USE_CASE env var to select: engineering_docs (default) or filter_design
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder

_uc_search = config.uc_search_config()
_uc_agent = config.uc_agent_config()["agent"]
_use_case = config.get_use_case()

SEARCH_ENDPOINT = config.search_endpoint()
INDEX_NAME = _uc_search["chunked_index"]["name"]
SEMANTIC_CONFIG_NAME = _uc_search["chunked_index"]["semantic_config_name"]
PROJECT_ENDPOINT = config.project_endpoint()
AGENT_NAME = _uc_agent["name"]

# Use-case-specific test queries
_QUERIES = {
    "engineering_docs": {
        "keyword": [
            "Surfscan SP7 particle detection",
            "FinFET inspection post-etch defect",
            "3nm technology node scratch detection",
            "CMP process wafer inspection FAIL",
            "overlay metrology Archer 700",
        ],
        "semantic": [
            "What are the most common defect types found during wafer inspection?",
            "Which test cases failed and what corrective actions were recommended?",
            "How does the Surfscan system detect crystal originated particles?",
            "What is the acceptance criteria for 5nm node patterned wafer inspection?",
            "Show me test results for post-CMP contamination inspection",
        ],
        "agent": [
            "What defect types are detected by the Surfscan SP7 system?",
            "List all test cases that failed for 3nm technology node.",
            "What are the corrective actions for high nuisance rates?",
        ],
    },
    "filter_design": {
        "keyword": [
            "SAW filter Band 7 insertion loss",
            "BAW FBAR 5G NR n77",
            "TC-SAW temperature compensation",
            "duplexer isolation rejection",
            "LiNbO3 substrate Q factor",
        ],
        "semantic": [
            "What filter designs target 5G NR sub-6 GHz bands?",
            "Which filter test cases failed and what corrective actions were recommended?",
            "How does temperature affect SAW filter frequency stability?",
            "What are the acceptance criteria for BAW filter insertion loss?",
            "Show me test results for WiFi 6E coexistence filters",
        ],
        "agent": [
            "What are the design parameters for Band 7 SAW filters?",
            "List all filter designs that failed acceptance criteria.",
            "What corrective actions are recommended for high insertion loss?",
        ],
    },
}


def test_keyword_search(search_client: SearchClient):
    """Test keyword search queries."""
    print("=" * 60)
    print("KEYWORD SEARCH TESTS")
    print("=" * 60)

    queries = _QUERIES[_use_case]["keyword"]

    for query in queries:
        print(f"\n--- Query: '{query}' ---")
        results = search_client.search(
            search_text=query,
            top=3,
            include_total_count=True,
        )

        count = 0
        for result in results:
            count += 1
            name = result.get("metadata_storage_name", "N/A")
            score = result.get("@search.score", 0)
            content_preview = result.get("content", "")[:200]
            print(f"  [{count}] {name} (score: {score:.4f})")
            print(f"      {content_preview}...")

        if count == 0:
            print("  No results found.")
        print(f"  Total matches: {count}")


def test_semantic_search(search_client: SearchClient):
    """Test semantic search queries."""
    print("\n" + "=" * 60)
    print("SEMANTIC SEARCH TESTS")
    print("=" * 60)

    queries = _QUERIES[_use_case]["semantic"]

    for query in queries:
        print(f"\n--- Query: '{query}' ---")
        results = search_client.search(
            search_text=query,
            query_type="semantic",
            semantic_configuration_name=SEMANTIC_CONFIG_NAME,
            top=3,
            include_total_count=True,
        )

        count = 0
        for result in results:
            count += 1
            name = result.get("metadata_storage_name", "N/A")
            score = result.get("@search.reranker_score", result.get("@search.score", 0))
            content_preview = result.get("content", "")[:200]
            print(f"  [{count}] {name} (reranker score: {score:.4f})")
            print(f"      {content_preview}...")

        if count == 0:
            print("  No results found.")
        print(f"  Total matches: {count}")


def test_agent(project_client: AIProjectClient):
    """Test the Foundry agent with AI Search function-tool grounding."""
    print("\n" + "=" * 60)
    print("FOUNDRY AGENT TESTS (AI Search Function Tool)")
    print("=" * 60)

    from scripts.create_agent import query_agent

    credential = DefaultAzureCredential()
    test_prompts = _QUERIES[_use_case]["agent"]

    for prompt in test_prompts:
        print(f"\n--- Prompt: '{prompt}' ---")
        response = query_agent(prompt, credential=credential)
        if response:
            print(f"  Agent Response:\n  {response[:800]}")
            if len(response) > 800:
                print("  ... (truncated)")
        else:
            print("  No response.")


def main():
    credential = DefaultAzureCredential()

    # Test AI Search directly
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=credential,
    )

    test_keyword_search(search_client)
    test_semantic_search(search_client)

    # Test the Foundry agent
    project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=credential,
    )

    test_agent(project_client)

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
