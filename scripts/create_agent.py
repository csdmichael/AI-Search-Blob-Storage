"""
Create a Foundry Agent named 'Eng-Docs-Search-Agent' that uses
Azure AI Search as its only tool/knowledge source.

The agent is configured to:
- Only answer from the AI Search index
- Not make up any answers
- Not use web search
"""

import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import (
    AzureAISearchToolDefinition,
    AzureAISearchToolResource,
    AISearchIndexResource,
    AzureAISearchQueryType,
    ToolResources,
)

PROJECT_ENDPOINT = "https://001-ai-poc.services.ai.azure.com/api/projects/001-ai-proj"
AGENT_NAME = "Eng-Docs-Search-Agent"
AI_SEARCH_INDEX_NAME = "engineering-docs-index"

# The connection name for AI Search in your Foundry project
# Update this to match your actual connection name in the Foundry project
AI_SEARCH_CONNECTION_NAME = os.environ.get("AZURE_AI_SEARCH_CONNECTION_NAME", "aisearchmymmcjmu")

MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

AGENT_INSTRUCTIONS = """You are the Engineering Documents Search Agent for KLA manufacturing test cases.

STRICT RULES:
1. You MUST ONLY use the Azure AI Search index as your knowledge source.
2. You MUST NOT make up, fabricate, or hallucinate any information.
3. You MUST NOT use web search or any external sources.
4. If the information is not found in the search index, respond with:
   "I could not find relevant information in the engineering documents index. Please refine your query or check if the document exists in the system."
5. Always cite your sources using inline references in the format [doc_name†source] after every claim.
   Example: "The capture rate was 97.2% [KLA-MFG-TC-0042.txt†engineering-docs-index]."
6. Provide accurate, concise answers based solely on the indexed engineering documents.
7. When multiple documents are relevant, summarize findings and cite each document inline.
8. At the end of your response, list all referenced documents under a "Sources" heading.

You help engineers find information about:
- Manufacturing test cases and procedures
- Defect detection and classification results
- Inspection system configurations and recipes
- Quality assurance acceptance criteria
- Test results and corrective actions
- KLA inspection and metrology equipment specifications
"""


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
                    )
                ]
            )
        ),
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
