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

# Matches [source†index] citations from Foundry agent responses
_ANNOTATION_PATTERN = re.compile(r"\[([^\[\]\u2020]+?)\u2020([^\[\]]+?)\]")
# Legacy prefix-based doc ID patterns (blob storage use cases)
_PREFIX_DOC_PATTERN = re.compile(r"\b((?:MFG|FD)-TC-\d{4})\b")
_VALID_USE_CASES = set(config.VALID_USE_CASES)
_FALLBACK_PHRASES = [
    "could not find relevant information",
    "no relevant information",
    "I don't have",
    "not found in",
]


def _extract_sources(text: str) -> list[str]:
    """Pull document IDs from agent response text.

    Extracts from [source†index] annotations (all use cases) and
    standalone MFG-TC / FD-TC prefixed IDs.
    """
    sources: list[str] = []
    # Extract from [source†index] annotations
    for m in _ANNOTATION_PATTERN.finditer(text):
        src = m.group(1).strip()
        # Remove file extension for consistent doc_id
        doc_id = re.sub(r"\.(txt|json|pdf|pptx?)$", "", src, flags=re.IGNORECASE)
        sources.append(doc_id)
    # Also extract standalone prefix-based doc IDs
    for m in _PREFIX_DOC_PATTERN.finditer(text):
        if m.group(1) not in sources:
            sources.append(m.group(1))
    return list(dict.fromkeys(sources))


def _is_fallback(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in _FALLBACK_PHRASES)


def _extract_expected_doc_ids(prompt: str) -> list[str]:
    """Extract specific document IDs mentioned in the prompt."""
    return list(dict.fromkeys(m.upper() for m in _PREFIX_DOC_PATTERN.findall(prompt)))


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


# ── Cosmos DB helpers ───────────────────────────────────────────────

_cosmosdb_container = None


def _get_cosmosdb_container():
    """Lazily create and cache a Cosmos DB container client."""
    global _cosmosdb_container
    if _cosmosdb_container is None:
        from azure.cosmos import CosmosClient
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        cosmosdb_cfg = config.cosmosdb_config()
        endpoint = f"https://{cosmosdb_cfg['account_name']}.documents.azure.com:443/"
        client = CosmosClient(endpoint, credential=credential)
        database = client.get_database_client(cosmosdb_cfg["database_name"])
        _cosmosdb_container = database.get_container_client(cosmosdb_cfg["container_name"])
    return _cosmosdb_container


def _list_cosmosdb_documents(use_case: str) -> list[dict]:
    """Fetch document list from Cosmos DB for a use case."""
    container = _get_cosmosdb_container()
    doc_cfg = config.uc_document_config(use_case)
    file_filter = doc_cfg.get("cosmosdb_filter", "")

    if file_filter:
        query = f"SELECT c.id, c.fileName, c.state, c.stateName, c.status, c.overallConfidence, c.confidenceCategory FROM c WHERE CONTAINS(LOWER(c.fileName), '.{file_filter}')"
    else:
        query = "SELECT c.id, c.fileName, c.state, c.stateName, c.status, c.overallConfidence, c.confidenceCategory FROM c"

    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    docs = []
    for item in sorted(items, key=lambda x: x.get("fileName", "")):
        file_name = item.get("fileName", "")
        doc_id = os.path.splitext(file_name)[0]
        ext = os.path.splitext(file_name)[1].lstrip(".").lower()
        entry = {
            "filename": file_name,
            "doc_id": doc_id,
            "type": ext or doc_cfg.get("file_format", ""),
            "size_kb": 0,
            "title": file_name,
            "status": item.get("status", ""),
            "document_number": doc_id,
            "state": item.get("stateName", item.get("state", "")),
            "confidence": item.get("confidenceCategory", ""),
        }
        docs.append(entry)
    return docs


def _get_cosmosdb_document(doc_id: str, use_case: str) -> dict | None:
    """Fetch a single document from Cosmos DB by fileName (without extension)."""
    container = _get_cosmosdb_container()
    doc_cfg = config.uc_document_config(use_case)
    file_filter = doc_cfg.get("cosmosdb_filter", "")

    # Try matching fileName starting with doc_id
    query = "SELECT * FROM c WHERE STARTSWITH(c.fileName, @docId)"
    parameters = [{"name": "@docId", "value": doc_id}]
    items = list(container.query_items(
        query=query, parameters=parameters, enable_cross_partition_query=True
    ))

    if items:
        return items[0]

    # Fallback: try matching Cosmos DB id directly
    query = "SELECT * FROM c WHERE c.id = @docId"
    items = list(container.query_items(
        query=query, parameters=parameters, enable_cross_partition_query=True
    ))
    return items[0] if items else None


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
    if req.use_case not in _VALID_USE_CASES:
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
    if req.use_case not in _VALID_USE_CASES:
        raise HTTPException(status_code=400, detail=f"Invalid use_case: {req.use_case}")

    doc_prefix = config.uc_document_config(req.use_case)["document_prefix"]
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
        elif not config.is_cosmosdb_use_case(req.use_case) and not any(s.startswith(doc_prefix) for s in sources):
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


# ── Document browser endpoints ──────────────────────────────────────

@app.get("/api/documents")
def list_documents(use_case: str = "engineering_docs"):
    """List all documents for a use case with metadata."""
    if use_case not in _VALID_USE_CASES:
        raise HTTPException(status_code=400, detail=f"Invalid use_case: {use_case}")

    # Cosmos DB use cases: fetch document list from Cosmos DB
    if config.is_cosmosdb_use_case(use_case):
        try:
            docs = _list_cosmosdb_documents(use_case)
            return {"use_case": use_case, "total": len(docs), "documents": docs}
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Cosmos DB query failed for {use_case}: {exc}",
            )

    # Blob storage use cases: read from local filesystem
    data_dir = config.uc_data_dir(use_case)
    doc_cfg = config.uc_document_config(use_case)
    prefix = doc_cfg["document_prefix"]
    docs = []
    for f in sorted(os.listdir(data_dir)):
        if not f.startswith(prefix):
            continue
        path = os.path.join(data_dir, f)
        ext = os.path.splitext(f)[1].lower()
        doc_id = os.path.splitext(f)[0]
        entry = {"filename": f, "doc_id": doc_id, "type": ext.lstrip("."), "size_kb": round(os.path.getsize(path) / 1024, 1)}
        if ext == ".json":
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    meta = json.load(fh)
                entry["title"] = meta.get("title", "")
                entry["status"] = meta.get("status", "")
                entry["document_number"] = meta.get("document_number", doc_id)
            except Exception:
                pass
        docs.append(entry)
    return {"use_case": use_case, "total": len(docs), "documents": docs}


@app.get("/api/documents/{doc_id:path}")
def get_document(doc_id: str, use_case: str = "engineering_docs"):
    """Get document content by ID."""
    if use_case not in _VALID_USE_CASES:
        raise HTTPException(status_code=400, detail=f"Invalid use_case: {use_case}")

    # Cosmos DB use cases: fetch from Cosmos DB
    if config.is_cosmosdb_use_case(use_case):
        try:
            doc = _get_cosmosdb_document(doc_id, use_case)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Cosmos DB query failed: {exc}",
            )
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in Cosmos DB")
        # Format sections for display
        sections = {}
        for section in doc.get("sections", []):
            sec_name = section.get("sectionName", "Unknown Section")
            fields = section.get("fields", [])
            field_text = "\n".join(
                f"{f.get('fieldName', '')}: {f.get('correctedValue') or f.get('extractedValue', '')}"
                for f in fields if f.get("fieldName")
            )
            sections[sec_name] = field_text
        content = {
            "title": doc.get("fileName", doc_id),
            "status": doc.get("status", ""),
            "state": doc.get("state", ""),
            "stateName": doc.get("stateName", ""),
            "overallConfidence": doc.get("overallConfidence", 0),
            "confidenceCategory": doc.get("confidenceCategory", ""),
            "sections": sections,
        }
        return {"format": "json", "doc_id": doc_id, "content": content}

    # Blob storage use cases: read from local filesystem
    data_dir = config.uc_data_dir(use_case)
    json_path = os.path.join(data_dir, f"{doc_id}.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return {"format": "json", "doc_id": doc_id, "content": json.load(f)}
    txt_path = os.path.join(data_dir, f"{doc_id}.txt")
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            return {"format": "text", "doc_id": doc_id, "content": f.read()}
    raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")


from fastapi.responses import FileResponse  # noqa: E402


@app.get("/api/documents/{doc_id:path}/pdf")
def get_document_pdf(doc_id: str, use_case: str = "engineering_docs"):
    """Serve the raw PDF file for in-browser viewing."""
    if use_case not in _VALID_USE_CASES:
        raise HTTPException(status_code=400, detail=f"Invalid use_case: {use_case}")
    data_dir = config.uc_data_dir(use_case)
    pdf_path = os.path.join(data_dir, f"{doc_id}.pdf")
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf", filename=f"{doc_id}.pdf")
    raise HTTPException(status_code=404, detail=f"PDF {doc_id}.pdf not found")
