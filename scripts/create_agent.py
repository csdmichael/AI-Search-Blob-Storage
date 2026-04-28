"""
Create a Foundry Agent that uses Azure AI Search as its only tool/knowledge source.

The agent is configured to:
- Only answer from the AI Search index
- Not make up any answers
- Not use web search

Set USE_CASE env var to select: engineering_docs (default) or filter_design
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import (
    AzureAISearchToolDefinition,
    AzureAISearchToolResource,
    AISearchIndexResource,
    AzureAISearchQueryType,
    ToolResources,
)

_uc_agent = config.uc_agent_config()["agent"]

PROJECT_ENDPOINT = config.project_endpoint()
AGENT_NAME = _uc_agent["name"]
AI_SEARCH_INDEX_NAME = _uc_agent["search_index"]

# The connection name for AI Search in your Foundry project
AI_SEARCH_CONNECTION_NAME = os.environ.get("AZURE_AI_SEARCH_CONNECTION_NAME", "aisearchmymmcjmu")

MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", _uc_agent["model_deployment"])

AGENT_INSTRUCTIONS = _uc_agent["instructions"]


def main():
    print(f"Connecting to Foundry project: {PROJECT_ENDPOINT}")
    credential = DefaultAzureCredential()

    project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=credential,
    )

    # Get the AI Search connection from the Foundry project
    print(f"Looking up AI Search connection: {AI_SEARCH_CONNECTION_NAME}")
    try:
        search_connection = project_client.connections.get(AI_SEARCH_CONNECTION_NAME)
        print(f"Found connection: {search_connection.id}")
    except Exception as e:
        print(f"Error: Could not find AI Search connection '{AI_SEARCH_CONNECTION_NAME}'.")
        print(f"Available connections can be listed in the Azure AI Foundry portal.")
        print(f"Set the AZURE_AI_SEARCH_CONNECTION_NAME environment variable to the correct name.")
        raise

    # Create the agent with AI Search as the only tool
    print(f"\nCreating agent: {AGENT_NAME}")
    agent = project_client.agents.create_agent(
        model=MODEL_DEPLOYMENT_NAME,
        name=AGENT_NAME,
        instructions=AGENT_INSTRUCTIONS,
        tools=[AzureAISearchToolDefinition()],
        tool_resources=ToolResources(
            azure_ai_search=AzureAISearchToolResource(
                index_list=[
                    AISearchIndexResource(
                        index_connection_id=search_connection.id,
                        index_name=AI_SEARCH_INDEX_NAME,
                        query_type=AzureAISearchQueryType.SEMANTIC,
                        top_k=3,
                    )
                ]
            )
        ),
        temperature=0,
    )

    print(f"\nAgent created successfully!")
    print(f"  Agent ID:   {agent.id}")
    print(f"  Agent Name: {agent.name}")
    print(f"  Model:      {agent.model}")
    print(f"  Tools:      Azure AI Search (index: {AI_SEARCH_INDEX_NAME})")
    print(f"\nThe agent is configured to ONLY use AI Search - no web search or fabricated answers.")

    return agent


if __name__ == "__main__":
    main()
