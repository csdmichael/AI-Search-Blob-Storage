"""
Create and query Foundry agents configured with the native Azure AI Search tool.

This script uses chunked indexes per use case and deploys agents with:
- AzureAISearchToolDefinition (native Foundry tool)
- ToolResources.azure_ai_search -> AzureAISearchToolResource(index_list=[...])

Set USE_CASE env var to select: engineering_docs (default) or filter_design.
Optional env vars:
- AZURE_AI_SEARCH_CONNECTION_ID: Full Foundry connection resource ID
- AZURE_AI_SEARCH_CONNECTION_NAME: Foundry connection name (default: aisearchmymmcjmu)
- SEARCH_TOP_K: Number of retrieved chunks (default: 8)
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    AzureAISearchToolDefinition,
    ToolResources,
    AzureAISearchToolResource,
    AISearchIndexResource,
    AzureAISearchQueryType,
    ListSortOrder,
)

_uc_agent = config.uc_agent_config()["agent"]
_uc_search = config.uc_search_config()
_use_case = config.get_use_case()

PROJECT_ENDPOINT = config.project_endpoint()
AGENT_NAME = _uc_agent["name"]
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", _uc_agent["model_deployment"])
AGENT_INSTRUCTIONS = _uc_agent["instructions"]
CHUNKED_INDEX = _uc_search["chunked_index"]["name"]
SEARCH_TOP_K = int(os.environ.get("SEARCH_TOP_K", "16" if _use_case == "filter_design" else "8"))

if _use_case == "filter_design":
    DEFAULT_QUERY_TYPE = AzureAISearchQueryType.SEMANTIC
    QUERY_TYPE_LABEL = "semantic"
    AGENT_INSTRUCTIONS += (
        "\n\nGROUNDING POLICY: "
        "Always answer strictly from azure_ai_search retrieved chunks for filter-design documents. "
        "For document-specific queries (FD-TC-XXXX), prioritize chunks from that same document ID. "
        "If chunks for the requested FD-TC document are present, do not return a generic not-found response. "
        "For numeric fields, copy exact values from the retrieved text and keep units unchanged. "
        "When multiple similarly named numeric fields exist (for example measured values vs targets/specs), prefer the field that directly matches the user term. "
        "Prefer section-consistent extraction: design values from DESIGN PARAMETERS, measured values from TEST RESULTS, "
        "and actions from CORRECTIVE ACTIONS. "
        "Resolve common telecom terminology variants when matching intent, including n78 = Band 78 = Band 7 context where applicable in the corpus. "
        "If relevant chunks are present, provide the best grounded answer instead of generic fallback text."
    )
else:
    DEFAULT_QUERY_TYPE = AzureAISearchQueryType.SEMANTIC
    QUERY_TYPE_LABEL = "semantic"

# Cached ID avoids listing agents repeatedly during multi-prompt retests.
_AGENT_ID_CACHE: str | None = None


def _resolve_search_connection_id(project_client: AgentsClient) -> str:
    """Resolve Foundry AI Search connection ID from env var ID or connection name."""
    explicit_id = os.environ.get("AZURE_AI_SEARCH_CONNECTION_ID", "").strip()
    if explicit_id:
        return explicit_id

    connection_name = os.environ.get("AZURE_AI_SEARCH_CONNECTION_NAME", "aisearchmymmcjmu").strip()

    # Build ID deterministically to avoid intermittent hangs in connections.list().
    subscription_id = config.azure_resources()["subscription_id"]
    resource_group = config.azure_resources()["resource_group"]
    endpoint = config.project_endpoint()
    # Example endpoint: https://001-ai-poc.services.ai.azure.com/api/projects/001-ai-proj
    foundry_account = endpoint.split("//", 1)[1].split(".", 1)[0]
    project_name = endpoint.rstrip("/").split("/")[-1]
    candidate_id = (
        f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        f"/providers/Microsoft.CognitiveServices/accounts/{foundry_account}"
        f"/projects/{project_name}/connections/{connection_name}"
    )

    if os.environ.get("FORCE_DISCOVER_CONNECTION", "0") == "1":
        for conn in project_client.connections.list():
            name = getattr(conn, "name", "")
            conn_id = getattr(conn, "id", "")
            if name == connection_name:
                return conn_id

    return candidate_id


def _get_agent_by_name(project_client: AgentsClient, agent_name: str):
    """Get an agent by name with basic retry handling for transient service issues."""
    for _ in range(3):
        try:
            for agent in project_client.list_agents():
                if agent.name == agent_name:
                    return agent
            return None
        except Exception:
            time.sleep(1.0)
    return None


def query_agent(prompt: str, credential=None):
    """Query the deployed Foundry agent configured with native Azure AI Search tool."""
    global _AGENT_ID_CACHE

    if credential is None:
        credential = DefaultAzureCredential()
    project_client = AgentsClient(endpoint=PROJECT_ENDPOINT, credential=credential)

    agent_id = _AGENT_ID_CACHE
    if not agent_id:
        agent = _get_agent_by_name(project_client, AGENT_NAME)
        if not agent:
            print(f"Agent '{AGENT_NAME}' not found. Run create_agent.py first.")
            return None
        agent_id = agent.id
        _AGENT_ID_CACHE = agent_id

    wrapped_prompt = prompt
    if _use_case == "filter_design":
        wrapped_prompt = (
            "Use azure_ai_search results as the only source of truth. "
            "For FD-TC-specific questions, prioritize chunks from that document. "
            "If chunks for the requested document exist, do not answer with a generic not-found response. "
            "Copy exact numeric values and units from retrieved text, and keep section semantics consistent. "
            "Treat notation variants as equivalent when searching intent (e.g., n78, Band 78, and Band 7 context). "
            f"\n\nUser question: {prompt}"
        )

    thread = project_client.threads.create()
    project_client.messages.create(thread_id=thread.id, role="user", content=wrapped_prompt)

    run = project_client.runs.create(thread_id=thread.id, agent_id=agent_id)

    start_time = time.time()
    while True:
        if time.time() - start_time > 240:
            return "Run timed out while waiting for agent completion."

        try:
            run = project_client.runs.get(thread_id=thread.id, run_id=run.id)
        except Exception:
            time.sleep(1.0)
            continue

        if run.status == "completed":
            break
        if run.status == "failed":
            return f"Run failed: {run.last_error}"
        if run.status in ("cancelled", "expired"):
            return f"Run ended with status: {run.status}"

        # Native Azure AI Search tool is executed server-side, so no tool-output loop is needed.
        time.sleep(0.6)

    response_text = ""
    for msg in project_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING):
        if msg.role == "assistant" and msg.text_messages:
            response_text = msg.text_messages[-1].text.value
            break

    return response_text


def main():
    print(f"Connecting to Foundry project: {PROJECT_ENDPOINT}")
    credential = DefaultAzureCredential()
    project_client = AgentsClient(endpoint=PROJECT_ENDPOINT, credential=credential)

    connection_id = _resolve_search_connection_id(project_client)

    ai_search_index = AISearchIndexResource(
        index_connection_id=connection_id,
        index_name=CHUNKED_INDEX,
        query_type=DEFAULT_QUERY_TYPE,
        top_k=SEARCH_TOP_K,
    )

    tool_resources = ToolResources(
        azure_ai_search=AzureAISearchToolResource(
            index_list=[ai_search_index],
        )
    )

    for agent in project_client.list_agents():
        if agent.name == AGENT_NAME:
            project_client.delete_agent(agent.id)
            print(f"Deleted existing agent: {agent.id}")

    print(f"\nCreating agent: {AGENT_NAME}")
    created = project_client.create_agent(
        model=MODEL_DEPLOYMENT_NAME,
        name=AGENT_NAME,
        instructions=AGENT_INSTRUCTIONS,
        tools=[AzureAISearchToolDefinition()],
        tool_resources=tool_resources,
        temperature=0,
    )

    print("\nAgent created successfully!")
    print(f"  Agent ID:     {created.id}")
    print(f"  Agent Name:   {created.name}")
    print(f"  Model:        {created.model}")
    print(f"  Tool:         azure_ai_search (native)")
    print(f"  Connection:   {connection_id}")
    print(f"  Index:        {CHUNKED_INDEX}")
    print(f"  Query type:   {QUERY_TYPE_LABEL}")
    print(f"  top_k:        {SEARCH_TOP_K}")

    return created


if __name__ == "__main__":
    main()
