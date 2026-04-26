"""
Test the AI Search index with semantic and keyword search queries,
and test the Foundry agent with sample prompts.
"""

import os
import time
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder

SEARCH_ENDPOINT = "https://ai-search-my.search.windows.net"
INDEX_NAME = "engineering-docs-index"
PROJECT_ENDPOINT = "https://001-ai-poc.services.ai.azure.com/api/projects/001-ai-proj"
AGENT_NAME = "Eng-Docs-Search-Agent"


def test_keyword_search(search_client: SearchClient):
    """Test keyword search queries."""
    print("=" * 60)
    print("KEYWORD SEARCH TESTS")
    print("=" * 60)

    queries = [
        "Surfscan SP7 particle detection",
        "FinFET inspection post-etch defect",
        "3nm technology node scratch detection",
        "CMP process wafer inspection FAIL",
        "overlay metrology Archer 700",
    ]

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

    queries = [
        "What are the most common defect types found during wafer inspection?",
        "Which test cases failed and what corrective actions were recommended?",
        "How does the Surfscan system detect crystal originated particles?",
        "What is the acceptance criteria for 5nm node patterned wafer inspection?",
        "Show me test results for post-CMP contamination inspection",
    ]

    for query in queries:
        print(f"\n--- Query: '{query}' ---")
        results = search_client.search(
            search_text=query,
            query_type="semantic",
            semantic_configuration_name="engineering-docs-semantic-config",
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
    """Test the Foundry agent with sample prompts."""
    print("\n" + "=" * 60)
    print("FOUNDRY AGENT TESTS")
    print("=" * 60)

    # List agents to find ours
    agents = project_client.agents.list_agents()
    agent = None
    for a in agents:
        if a.name == AGENT_NAME:
            agent = a
            break

    if not agent:
        print(f"Agent '{AGENT_NAME}' not found. Run create_agent.py first.")
        return

    print(f"Found agent: {agent.name} (ID: {agent.id})")

    test_prompts = [
        "What defect types are detected by the Surfscan SP7 system?",
        "List all test cases that failed for 3nm technology node.",
        "What are the corrective actions for high nuisance rates?",
    ]

    for prompt in test_prompts:
        print(f"\n--- Prompt: '{prompt}' ---")

        thread = project_client.agents.threads.create()
        project_client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt,
        )

        run = project_client.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=agent.id,
        )

        if run.status == "failed":
            print(f"  Run failed: {run.last_error}")
            continue

        messages = project_client.agents.messages.list(
            thread_id=thread.id,
            order=ListSortOrder.ASCENDING,
        )

        for msg in messages:
            if msg.role == "assistant" and msg.text_messages:
                last_text = msg.text_messages[-1]
                response = last_text.text.value
                annotations = last_text.text.annotations if hasattr(last_text.text, "annotations") else []

                print(f"  Agent Response:\n  {response[:800]}")
                if len(response) > 800:
                    print("  ... (truncated)")

                # Display citations from annotations
                if annotations:
                    print(f"\n  Citations ({len(annotations)}):")
                    for ann in annotations:
                        if hasattr(ann, "url_citation") and ann.url_citation:
                            title = getattr(ann.url_citation, "title", "")
                            url = getattr(ann.url_citation, "url", "")
                            print(f"    - {title or 'Source'}: {url}")
                        elif hasattr(ann, "file_citation") and ann.file_citation:
                            fid = getattr(ann.file_citation, "file_id", "")
                            print(f"    - File: {fid}")
                        else:
                            print(f"    - {ann}")


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
