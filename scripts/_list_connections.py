"""List all connections in the Foundry project."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

client = AIProjectClient(
    endpoint=config.project_endpoint(),
    credential=DefaultAzureCredential(),
)
connections = client.connections.list()
for c in connections:
    target = getattr(c.properties, "target", "N/A")
    print(f"{c.name} | type={c.properties.category} | target={target}")
