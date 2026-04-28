"""Test the exact queries that were returning wrong answers."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["USE_CASE"] = "filter_design"

from azure.identity import DefaultAzureCredential
from scripts.create_agent import query_agent

cred = DefaultAzureCredential()

queries = [
    "What is the Q factor for FD-TC-0003?",
    "What is the insertion loss for FD-TC-0003?",
    "What are the design parameters for FD-TC-0003?",
    "What is the measured return loss for FD-TC-0003?",
]

for q in queries:
    print(f"\n{'='*60}")
    print(f"Q: {q}")
    print(f"{'='*60}")
    resp = query_agent(q, credential=cred)
    print(f"A: {resp}")
