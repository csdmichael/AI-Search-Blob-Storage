"""
Centralized configuration loader.

All project settings are stored in JSON files under the config/ directory.
Scripts import from here instead of hardcoding values.

Set the USE_CASE environment variable to select a use case:
  - "engineering_docs"  (default) — Manufacturing inspection test cases
  - "filter_design"               — RF filter design documents
"""

import os
import json

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")

DEFAULT_USE_CASE = "engineering_docs"
VALID_USE_CASES = ("engineering_docs", "filter_design")


def _load(filename: str) -> dict:
    """Load a JSON config file from the config directory."""
    path = os.path.join(CONFIG_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Lazy-loaded config singletons ──────────────────────────────────

_cache: dict[str, dict] = {}


def _get(filename: str) -> dict:
    if filename not in _cache:
        _cache[filename] = _load(filename)
    return _cache[filename]


def get_use_case() -> str:
    """Return the active use case from USE_CASE env var (default: engineering_docs)."""
    uc = os.environ.get("USE_CASE", DEFAULT_USE_CASE)
    if uc not in VALID_USE_CASES:
        raise ValueError(f"Invalid USE_CASE '{uc}'. Must be one of {VALID_USE_CASES}")
    return uc


def azure_resources() -> dict:
    return _get("azure_resources.json")


def storage_config() -> dict:
    return _get("storage_config.json")


def search_config() -> dict:
    return _get("search_config.json")


def agent_config() -> dict:
    return _get("agent_config.json")


def document_config() -> dict:
    return _get("document_config.json")


def prompts_config() -> dict:
    return _get("prompts_config.json")


# ── Use-case-aware helpers ─────────────────────────────────────────

def uc_document_config(use_case: str | None = None) -> dict:
    """Return document config for the given (or active) use case."""
    uc = use_case or get_use_case()
    return document_config()["use_cases"][uc]


def uc_search_config(use_case: str | None = None) -> dict:
    """Return search config for the given (or active) use case."""
    uc = use_case or get_use_case()
    return search_config()["use_cases"][uc]


def uc_agent_config(use_case: str | None = None) -> dict:
    """Return agent config for the given (or active) use case."""
    uc = use_case or get_use_case()
    return agent_config()["use_cases"][uc]


def uc_data_dir(use_case: str | None = None) -> str:
    """Return the data subfolder path for the given (or active) use case."""
    doc_cfg = uc_document_config(use_case)
    return os.path.join(DATA_DIR, doc_cfg["data_subfolder"])


_UC_FOLDER_MAP = {"engineering_docs": "engineering-docs", "filter_design": "filter-design"}


def uc_docs_dir(use_case: str | None = None) -> str:
    """Return the use-case-specific docs folder (use-cases/<uc>/)."""
    uc = use_case or get_use_case()
    return os.path.join(PROJECT_ROOT, "use-cases", _UC_FOLDER_MAP[uc])


# ── Convenience helpers ────────────────────────────────────────────

def storage_account_name() -> str:
    return azure_resources()["storage"]["account_name"]


def storage_url() -> str:
    return f"https://{storage_account_name()}.blob.core.windows.net"


def storage_resource_id() -> str:
    return azure_resources()["storage"]["resource_id"]


def search_endpoint() -> str:
    return azure_resources()["search"]["endpoint"]


def project_endpoint() -> str:
    return azure_resources()["foundry"]["project_endpoint"]


def container_name(use_case: str | None = None) -> str:
    uc = use_case or get_use_case()
    return storage_config()["containers"][uc]
