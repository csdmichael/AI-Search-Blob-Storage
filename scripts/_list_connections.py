"""List all connections in the Foundry project."""
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

client = AIProjectClient(
    endpoint="https://001-ai-poc.services.ai.azure.com/api/projects/001-ai-proj",
    credential=DefaultAzureCredential(),
)
connections = client.connections.list()
for c in connections:
    target = getattr(c.properties, "target", "N/A")
    print(f"{c.name} | type={c.properties.category} | target={target}")
