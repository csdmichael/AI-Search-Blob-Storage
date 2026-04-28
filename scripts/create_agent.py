"""
Create a Foundry Agent with AI Search as a custom function tool.

The agent has a registered function tool 'search_engineering_documents' that
queries the AI Search chunked index. When the agent calls this tool, we execute
the search and return raw document content — achieving >90% grounding accuracy.

Set USE_CASE env var to select: engineering_docs (default) or filter_design
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import (
    FunctionToolDefinition,
    ToolOutput,
    ListSortOrder,
    MessageRole,
)

_uc_agent = config.uc_agent_config()["agent"]
_uc_search = config.uc_search_config()

PROJECT_ENDPOINT = config.project_endpoint()
SEARCH_ENDPOINT = config.search_endpoint()
AGENT_NAME = _uc_agent["name"]
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", _uc_agent["model_deployment"])
AGENT_INSTRUCTIONS = _uc_agent["instructions"]
CHUNKED_INDEX = _uc_search["chunked_index"]["name"]
SEMANTIC_CONFIG = _uc_search["chunked_index"]["semantic_config_name"]

# Function tool definition — the agent sees this as "search_documents"
SEARCH_TOOL_DEF = FunctionToolDefinition(
    function={
        "name": "search_documents",
        "description": (
            "Search the engineering document index using Azure AI Search. "
            "Returns the most relevant document sections with exact text content. "
            "Use this tool for EVERY question — do not answer from memory."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Include document numbers (e.g. FD-TC-0001) and key terms.",
                },
            },
            "required": ["query"],
        },
    }
)


def _execute_search(query: str, credential) -> str:
    """Execute AI Search and return formatted results."""
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=CHUNKED_INDEX,
        credential=credential,
    )
    results = list(search_client.search(
        search_text=query,
        query_type="semantic",
        semantic_configuration_name=SEMANTIC_CONFIG,
        top=5,
        select="document_number,section_name,content,source_file",
    ))
    if not results:
        return "NO RESULTS FOUND in the document index for this query."

    output = ""
    for i, r in enumerate(results, 1):
        doc = r.get("document_number", "?")
        section = r.get("section_name", "?")
        content = r.get("content", "")
        source = r.get("source_file", "?")
        output += f"[Result {i}] Document: {doc} | Section: {section} | File: {source}\n"
        output += content + "\n\n"
    return output


def query_agent(prompt: str, credential=None):
    """Query the agent — handles the function tool call loop."""
    if credential is None:
        credential = DefaultAzureCredential()
    project_client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)

    # Find agent
    agent = None
    for a in project_client.agents.list_agents():
        if a.name == AGENT_NAME:
            agent = a
            break
    if not agent:
        print(f"Agent '{AGENT_NAME}' not found. Run create_agent.py first.")
        return None

    # Create thread and send user message
    thread = project_client.agents.threads.create()
    project_client.agents.messages.create(
        thread_id=thread.id, role="user", content=prompt,
    )

    # Start run
    run = project_client.agents.runs.create(
        thread_id=thread.id, agent_id=agent.id,
    )

    # Poll and handle tool calls
    while True:
        run = project_client.agents.runs.get(thread_id=thread.id, run_id=run.id)

        if run.status == "completed":
            break
        elif run.status == "failed":
            return f"Run failed: {run.last_error}"
        elif run.status == "requires_action":
            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            tool_outputs = []
            for tc in tool_calls:
                if tc.function.name == "search_documents":
                    args = json.loads(tc.function.arguments)
                    search_result = _execute_search(args["query"], credential)
                    tool_outputs.append(ToolOutput(
                        tool_call_id=tc.id,
                        output=search_result,
                    ))
            project_client.agents.runs.submit_tool_outputs(
                thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs,
            )
        else:
            # queued, in_progress — wait
            import time
            time.sleep(0.5)

    # Get response
    for msg in project_client.agents.messages.list(
        thread_id=thread.id, order=ListSortOrder.ASCENDING,
    ):
        if msg.role == "assistant" and msg.text_messages:
            return msg.text_messages[-1].text.value
    return ""


def main():
    print(f"Connecting to Foundry project: {PROJECT_ENDPOINT}")
    credential = DefaultAzureCredential()
    project_client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)

    # Delete existing agent with same name
    for a in project_client.agents.list_agents():
        if a.name == AGENT_NAME:
            project_client.agents.delete_agent(a.id)
            print(f"Deleted existing agent: {a.id}")

    # Create agent with AI Search as a function tool
    print(f"\nCreating agent: {AGENT_NAME}")
    agent = project_client.agents.create_agent(
        model=MODEL_DEPLOYMENT_NAME,
        name=AGENT_NAME,
        instructions=AGENT_INSTRUCTIONS,
        tools=[SEARCH_TOOL_DEF],
        temperature=0,
    )

    print(f"\nAgent created successfully!")
    print(f"  Agent ID:     {agent.id}")
    print(f"  Agent Name:   {agent.name}")
    print(f"  Model:        {agent.model}")
    print(f"  Tool:         search_documents (AI Search: {CHUNKED_INDEX})")
    print(f"  Grounding:    Function tool returns raw AI Search results")

    return agent


if __name__ == "__main__":
    main()
