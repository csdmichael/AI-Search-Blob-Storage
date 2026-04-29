"""
FastAPI backend bridging the Angular UI to the existing Python agent scripts.

Endpoints:
  POST /api/chat          — Send a prompt to the agent, get a response
  GET  /api/prompts       — Get sample prompts per use case
  POST /api/batch         — Run multiple prompts sequentially, return results
  POST /api/feedback      — Submit relevance feedback for a search result
  GET  /api/feedback      — Get feedback entries
"""

import os
import sys
import time
import json
import re
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add project root to path so existing scripts/config can be imported
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import config  # noqa: E402

app = FastAPI(title="AI Search Agent API", version="1.0.0")

_ALLOWED_ORIGINS = [
    "https://ai-search-agent-ui.azurewebsites.net",
    "http://ai-search-agent-ui.azurewebsites.net",
    "http://localhost:8100",
    "http://localhost:4200",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Sample prompts (loaded from config/prompts_config.json) ─────────

def _load_prompts() -> dict[str, dict[str, list[dict]]]:
    return config.prompts_config()["use_cases"]

SAMPLE_PROMPTS = _load_prompts()


# ── Request / Response models ───────────────────────────────────────

class ChatRequest(BaseModel):
    prompt: str
    use_case: str = "engineering_docs"


class ChatResponse(BaseModel):
    prompt: str
    response: str
    use_case: str
    duration_ms: int
    sources: list[str] = []


class BatchRequest(BaseModel):
    prompts: list[str]
    use_case: str = "engineering_docs"


class BatchResultItem(BaseModel):
    prompt: str
    response: str
    duration_ms: int
    sources: list[str] = []
    passed: bool
    reason: str


class BatchResponse(BaseModel):
    use_case: str
    total: int
    passed: int
    failed: int
    accuracy_pct: float
    results: list[BatchResultItem]


class FeedbackRequest(BaseModel):
    query: str
    document_id: str
    relevant: bool
    score: float = 0.0
    notes: str = ""
    use_case: str = "engineering_docs"


class FeedbackEntry(BaseModel):
    timestamp: str
    query: str
    document_id: str
    relevant: bool
    search_score: float
    notes: str = ""


# ── Helpers ─────────────────────────────────────────────────────────

_DOC_ID_PATTERN = re.compile(r"((?:MFG|FD)-TC-\d{4})")
_FALLBACK_PHRASES = [
    "could not find relevant information",
    "no relevant information",
    "I don't have",
    "not found in",
]


def _extract_sources(text: str) -> list[str]:
    """Pull document IDs from agent response text."""
    return list(dict.fromkeys(_DOC_ID_PATTERN.findall(text)))


def _is_fallback(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in _FALLBACK_PHRASES)


def _extract_expected_doc_ids(prompt: str) -> list[str]:
    """Extract specific document IDs mentioned in the prompt."""
    return list(dict.fromkeys(_DOC_ID_PATTERN.findall(prompt.upper())))


def _query_agent(prompt: str, use_case: str) -> str:
    """Call the existing query_agent function with the right USE_CASE."""
    os.environ["USE_CASE"] = use_case

    # Force reimport to pick up new USE_CASE
    if "scripts.create_agent" in sys.modules:
        del sys.modules["scripts.create_agent"]

    from scripts.create_agent import query_agent
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()
    result = query_agent(prompt, credential=credential)
    return result or ""


def _feedback_file(use_case: str) -> str:
    return os.path.join(config.uc_data_dir(use_case), "feedback_log.json")


def _load_feedback(use_case: str) -> list[dict]:
    path = _feedback_file(use_case)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_feedback(use_case: str, entries: list[dict]):
    path = _feedback_file(use_case)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


# ── Endpoints ───────────────────────────────────────────────────────

@app.get("/api/prompts")
def get_prompts(use_case: str = "engineering_docs"):
    if use_case not in SAMPLE_PROMPTS:
        raise HTTPException(status_code=400, detail=f"Invalid use_case: {use_case}")
    return SAMPLE_PROMPTS[use_case]


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if req.use_case not in ("engineering_docs", "filter_design"):
        raise HTTPException(status_code=400, detail=f"Invalid use_case: {req.use_case}")

    start = time.time()
    response_text = _query_agent(req.prompt, req.use_case)
    duration = int((time.time() - start) * 1000)

    return ChatResponse(
        prompt=req.prompt,
        response=response_text,
        use_case=req.use_case,
        duration_ms=duration,
        sources=_extract_sources(response_text),
    )


@app.post("/api/batch", response_model=BatchResponse)
def batch_run(req: BatchRequest):
    if req.use_case not in ("engineering_docs", "filter_design"):
        raise HTTPException(status_code=400, detail=f"Invalid use_case: {req.use_case}")

    doc_prefix = "FD-TC" if req.use_case == "filter_design" else "MFG-TC"
    results: list[BatchResultItem] = []

    for prompt in req.prompts:
        start = time.time()
        response_text = _query_agent(prompt, req.use_case)
        duration = int((time.time() - start) * 1000)
        sources = _extract_sources(response_text)

        passed = True
        reason = "OK"

        if not response_text.strip():
            passed = False
            reason = "Empty response"
        elif _is_fallback(response_text):
            passed = False
            reason = "Agent returned fallback / not-found"
        elif not sources:
            passed = False
            reason = "No document citations in response"
        elif not any(s.startswith(doc_prefix) for s in sources):
            passed = False
            reason = f"No {doc_prefix} citations (wrong use-case docs)"
        else:
            # If prompt mentions specific doc IDs, verify they appear in the response
            expected_ids = _extract_expected_doc_ids(prompt)
            missing = [eid for eid in expected_ids if eid not in (s.upper() for s in sources)]
            if missing:
                passed = False
                reason = f"Expected doc(s) not cited: {', '.join(missing)}"

        results.append(BatchResultItem(
            prompt=prompt,
            response=response_text,
            duration_ms=duration,
            sources=sources,
            passed=passed,
            reason=reason,
        ))

    passed_count = sum(1 for r in results if r.passed)
    total = len(results)
    accuracy = (passed_count / total * 100) if total else 0.0

    return BatchResponse(
        use_case=req.use_case,
        total=total,
        passed=passed_count,
        failed=total - passed_count,
        accuracy_pct=round(accuracy, 1),
        results=results,
    )


@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    entries = _load_feedback(req.use_case)
    entries.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": req.query,
        "document_id": req.document_id,
        "relevant": req.relevant,
        "search_score": round(req.score, 4),
        "notes": req.notes,
    })
    _save_feedback(req.use_case, entries)
    return {"status": "ok", "total_entries": len(entries)}


@app.get("/api/feedback")
def get_feedback(use_case: str = "engineering_docs"):
    return _load_feedback(use_case)
