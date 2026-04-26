"""
Centralised configuration for all Azure resource names and settings.

All values are read from environment variables so nothing is hard-coded in
the script files.  Copy .env.example to .env, fill in your values, and the
scripts will pick them up automatically (python-dotenv loads the file).
"""

import os
from pathlib import Path

# Load .env from the repository root (if present) without raising an error
# when the file doesn't exist (e.g. in CI where secrets come from env vars).
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path, override=False)
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables

# ── Azure Subscription / Resource Group ──────────────────────────────────────
SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
RESOURCE_GROUP = os.environ.get("AZURE_RESOURCE_GROUP", "")

# ── Azure Blob Storage ────────────────────────────────────────────────────────
STORAGE_ACCOUNT_NAME = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME", "")
STORAGE_CONTAINER_NAME = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "engineering-docs")
STORAGE_URL = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
STORAGE_RESOURCE_ID = (
    f"/subscriptions/{SUBSCRIPTION_ID}"
    f"/resourceGroups/{RESOURCE_GROUP}"
    f"/providers/Microsoft.Storage/storageAccounts/{STORAGE_ACCOUNT_NAME}"
)

# ── Azure AI Search ───────────────────────────────────────────────────────────
SEARCH_SERVICE_NAME = os.environ.get("AZURE_SEARCH_SERVICE_NAME", "")
SEARCH_ENDPOINT = f"https://{SEARCH_SERVICE_NAME}.search.windows.net"
SEARCH_INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "engineering-docs-index")
SEARCH_CHUNKED_INDEX_NAME = os.environ.get("AZURE_SEARCH_CHUNKED_INDEX_NAME", "engineering-docs-chunked-index")
SEARCH_INDEXER_NAME = os.environ.get("AZURE_SEARCH_INDEXER_NAME", "engineering-docs-indexer")
SEARCH_DATA_SOURCE_NAME = os.environ.get("AZURE_SEARCH_DATA_SOURCE_NAME", "engineering-docs-blob-datasource")

# ── Azure AI Foundry ──────────────────────────────────────────────────────────
PROJECT_ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "")

# ── Foundry Agent ─────────────────────────────────────────────────────────────
AGENT_NAME = os.environ.get("AGENT_NAME", "Eng-Docs-Search-Agent")
AI_SEARCH_CONNECTION_NAME = os.environ.get("AZURE_AI_SEARCH_CONNECTION_NAME", "")
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4.1")
FINE_TUNE_BASE_MODEL = os.environ.get("FINE_TUNE_BASE_MODEL", "gpt-4.1")


def validate_required(names: list[str]) -> None:
    """Raise ValueError listing every required config key that is unset."""
    missing = [n for n in names if not globals().get(n)]
    if missing:
        raise ValueError(
            "The following required configuration values are not set. "
            "Copy .env.example to .env and fill in your values, or export "
            "the corresponding environment variables:\n"
            + "\n".join(f"  {n}" for n in missing)
        )
