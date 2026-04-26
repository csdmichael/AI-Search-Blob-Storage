"""List all connections in the Foundry project."""
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
import config

config.validate_required(["PROJECT_ENDPOINT"])

client = AIProjectClient(
    endpoint=config.PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)
connections = client.connections.list()
for c in connections:
    target = getattr(c.properties, "target", "N/A")
    print(f"{c.name} | type={c.properties.category} | target={target}")
