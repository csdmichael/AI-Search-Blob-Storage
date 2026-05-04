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
import re
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

_ANNOTATION_PATTERN = re.compile(r"\[[^\[\]†]+?†[^\[\]]+?\]")
_PREFIX_DOC_PATTERN = re.compile(r"\b((?:MFG|FD)-TC-\d{4})\b", re.IGNORECASE)
_FALLBACK_RESPONSES = {
    "engineering_docs": (
        "I could not find relevant information in the engineering documents index for this query. "
        "Please try a more specific query or verify the document exists."
    ),
    "filter_design": "I could not find relevant information in the filter design documents index for this query.",
    "tax_pdf_forms": (
        "I could not find relevant information in the tax exemption forms index for this query. "
        "Please try a more specific query or verify the document exists."
    ),
    "eng_design_ppt": (
        "I could not find relevant information in the engineering design presentations index for this query. "
        "Please try a more specific query or verify the document exists."
    ),
}

PROJECT_ENDPOINT = config.project_endpoint()
AGENT_NAME = _uc_agent["name"]
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", _uc_agent["model_deployment"])
AGENT_INSTRUCTIONS = _uc_agent["instructions"]
CHUNKED_INDEX = _uc_search["chunked_index"]["name"]
SEARCH_TOP_K = int(os.environ.get("SEARCH_TOP_K", "10"))

if _use_case in ("tax_pdf_forms", "eng_design_ppt") and "SEARCH_TOP_K" not in os.environ:
    SEARCH_TOP_K = 15

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
elif _use_case in ("tax_pdf_forms", "eng_design_ppt"):
    DEFAULT_QUERY_TYPE = AzureAISearchQueryType.SEMANTIC
    QUERY_TYPE_LABEL = "semantic"
    AGENT_INSTRUCTIONS += (
        "\n\nGROUNDING POLICY: "
        "Always answer strictly from azure_ai_search retrieved chunks. "
        "Never use web search, browser search, or any external source. "
        "Each chunk starts with 'Document: <fileName>' — use that fileName for citations. "
        "Never cite a URL, blob path, image asset, or external viewer; cite only the document fileName found in the retrieved chunk metadata. "
        "If relevant chunks are present, provide the best grounded answer instead of generic fallback text. "
        "When multiple chunks reference the same document, synthesize information across them. "
        "For field values, copy the EXACT text from the retrieved chunk content. "
        "When queried about a specific state or jurisdiction, prioritize chunks matching that state. "
        "If chunks contain relevant information, do NOT return a generic not-found response. "
        "Every factual sentence must include at least one citation in the format [fileName†index-name]. "
        "For deadline, expiration, validity, or renewal questions, inspect sections such as Exemption Details, Certification & Signature, Tax Information, or Full Document Summary for related dates and certificate metadata. "
        "If the documents do not state an explicit deadline or renewal workflow but do contain related dates, answer with those exact grounded dates and clearly state that no separate deadline or renewal instruction was found in the retrieved documents. "
        "Prefer a cited partial answer over an uncited generalization whenever the retrieved chunks are relevant."
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


def _tool_type_name(tool) -> str:
    """Normalize tool type across SDK model objects and plain dicts."""
    if isinstance(tool, dict):
        return str(tool.get("type", "")).strip().lower()
    return str(getattr(tool, "type", "")).strip().lower()


def _is_search_only_agent(agent) -> bool:
    """Ensure the deployed agent cannot use web or other external tools."""
    tools = list(getattr(agent, "tools", None) or [])
    if len(tools) != 1:
        return False
    return _tool_type_name(tools[0]) == "azure_ai_search"


def _fallback_response() -> str:
    return _FALLBACK_RESPONSES[_use_case]


def _response_is_grounded(response_text: str) -> bool:
    """Reject replies that do not contain grounded citations from the search corpus."""
    compact = " ".join(response_text.split())
    if not compact:
        return False
    if _ANNOTATION_PATTERN.search(compact):
        return True
    if _use_case in ("engineering_docs", "filter_design") and _PREFIX_DOC_PATTERN.search(compact):
        return True
    return False


def _build_search_only_agent(project_client: AgentsClient, connection_id: str):
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

    return project_client.create_agent(
        model=MODEL_DEPLOYMENT_NAME,
        name=AGENT_NAME,
        instructions=AGENT_INSTRUCTIONS,
        tools=[AzureAISearchToolDefinition()],
        tool_resources=tool_resources,
        temperature=0,
    )


def _ensure_search_only_agent(project_client: AgentsClient, connection_id: str):
    """Recreate the agent if it drifted from the intended search-only toolset."""
    agent = _get_agent_by_name(project_client, AGENT_NAME)
    if agent and _is_search_only_agent(agent):
        return agent

    if agent:
        project_client.delete_agent(agent.id)
        print(f"Deleted non-compliant agent: {agent.id}")

    created = _build_search_only_agent(project_client, connection_id)
    print(f"Created search-only agent: {created.id}")
    return created


def query_agent(prompt: str, credential=None):
    """Query the deployed Foundry agent configured with native Azure AI Search tool."""
    global _AGENT_ID_CACHE

    if credential is None:
        credential = DefaultAzureCredential()
    project_client = AgentsClient(endpoint=PROJECT_ENDPOINT, credential=credential)

    agent_id = _AGENT_ID_CACHE
    if not agent_id:
        connection_id = _resolve_search_connection_id(project_client)
        agent = _ensure_search_only_agent(project_client, connection_id)
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
    elif _use_case in ("tax_pdf_forms", "eng_design_ppt"):
        wrapped_prompt = (
            "Use azure_ai_search results as the only source of truth. "
            "Each chunk starts with 'Document: <fileName>' — use that fileName for citations. "
            "If relevant chunks are present, provide the best grounded answer. Do NOT return a generic not-found response. "
            "When synthesizing across multiple chunks, combine information and cite all referenced documents. "
            "Copy exact field values from retrieved text. "
            "Every factual sentence must include at least one citation. "
            "For deadline, expiration, validity, or renewal questions, search for related date fields such as Effective Date, Date, certificate metadata, and Exemption Details before concluding the information is missing. "
            "If the exact workflow is not present but related dates are present, state that limitation explicitly and still return the cited date evidence. "
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

    if not _response_is_grounded(response_text):
        return _fallback_response()

    return response_text


def main():
    print(f"Connecting to Foundry project: {PROJECT_ENDPOINT}")
    credential = DefaultAzureCredential()
    project_client = AgentsClient(endpoint=PROJECT_ENDPOINT, credential=credential)

    connection_id = _resolve_search_connection_id(project_client)

    for agent in project_client.list_agents():
        if agent.name == AGENT_NAME:
            project_client.delete_agent(agent.id)
            print(f"Deleted existing agent: {agent.id}")

    print(f"\nCreating agent: {AGENT_NAME}")
    created = _build_search_only_agent(project_client, connection_id)

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
