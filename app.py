"""
App Service entry point — FastAPI server.
This file contains the full API server inline to avoid module-path issues
on Azure App Service Linux where Oryx extracts to a temp directory.
"""
import os
import sys
import time
import json
import re
from datetime import datetime, timezone

# Ensure the project root is on sys.path for config and scripts imports
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402
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
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Sample prompts (loaded from config/prompts_config.json) ─────────

SAMPLE_PROMPTS = config.prompts_config()["use_cases"]


# ── Models ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    prompt: str
    use_case: str = "engineering_docs"

class ChatResponse(BaseModel):
    prompt: str
    response: str
    use_case: str
    duration_ms: int
    sources: list[str] = []
    attempts: int = 1

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


# ── Helpers ─────────────────────────────────────────────────────────

_DOC_ID_PATTERN = re.compile(r"((?:MFG|FD)-TC-\d{4}|tax_exemption_\w+\.pdf|filter_design_\w+\.pptx?)")
_VALID_USE_CASES = set(config.VALID_USE_CASES)
_FALLBACK_PHRASES = [
    "could not find relevant information",
    "no relevant information",
    "I don't have",
    "not found in",
]

def _extract_sources(text: str) -> list[str]:
    return list(dict.fromkeys(_DOC_ID_PATTERN.findall(text)))

def _is_fallback(text: str) -> bool:
    return any(p in text.lower() for p in _FALLBACK_PHRASES)

def _query_agent(prompt: str, use_case: str) -> str:
    os.environ["USE_CASE"] = use_case
    if "scripts.create_agent" in sys.modules:
        del sys.modules["scripts.create_agent"]
    from scripts.create_agent import query_agent
    from azure.identity import DefaultAzureCredential
    result = query_agent(prompt, credential=DefaultAzureCredential())
    return result or ""

def _query_agent_with_retry(prompt: str, use_case: str, max_retries: int = 3) -> tuple[str, int]:
    """Query agent with retry circuit breaker — retries on fallback/empty responses."""
    for attempt in range(1, max_retries + 1):
        result = _query_agent(prompt, use_case)
        if result.strip() and not _is_fallback(result):
            return result, attempt
        if attempt < max_retries:
            time.sleep(0.5)
    return result, max_retries

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
        docs.append({
            "filename": file_name,
            "doc_id": doc_id,
            "type": ext or doc_cfg.get("file_format", ""),
            "size_kb": 0,
            "title": file_name,
            "status": item.get("status", ""),
            "document_number": doc_id,
            "state": item.get("stateName", item.get("state", "")),
            "confidence": item.get("confidenceCategory", ""),
        })
    return docs


def _get_cosmosdb_document(doc_id: str) -> dict | None:
    """Fetch a single document from Cosmos DB by fileName (without extension)."""
    container = _get_cosmosdb_container()

    query = "SELECT * FROM c WHERE STARTSWITH(c.fileName, @docId)"
    parameters = [{"name": "@docId", "value": doc_id}]
    items = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True,
    ))

    if items:
        return items[0]

    query = "SELECT * FROM c WHERE c.id = @docId"
    items = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True,
    ))
    return items[0] if items else None


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
    response_text, attempts = _query_agent_with_retry(req.prompt, req.use_case)
    duration = int((time.time() - start) * 1000)
    return ChatResponse(
        prompt=req.prompt, response=response_text, use_case=req.use_case,
        duration_ms=duration, sources=_extract_sources(response_text),
        attempts=attempts,
    )

@app.post("/api/batch", response_model=BatchResponse)
def batch_run(req: BatchRequest):
    if req.use_case not in _VALID_USE_CASES:
        raise HTTPException(status_code=400, detail=f"Invalid use_case: {req.use_case}")
    results: list[BatchResultItem] = []
    for prompt in req.prompts:
        start = time.time()
        response_text = _query_agent(prompt, req.use_case)
        duration = int((time.time() - start) * 1000)
        sources = _extract_sources(response_text)
        passed, reason = True, "OK"
        if not response_text.strip():
            passed, reason = False, "Empty response"
        elif _is_fallback(response_text):
            passed, reason = False, "Agent returned fallback / not-found"
        elif not sources:
            passed, reason = False, "No document citations in response"
        results.append(BatchResultItem(
            prompt=prompt, response=response_text, duration_ms=duration,
            sources=sources, passed=passed, reason=reason,
        ))
    passed_count = sum(1 for r in results if r.passed)
    total = len(results)
    return BatchResponse(
        use_case=req.use_case, total=total, passed=passed_count,
        failed=total - passed_count,
        accuracy_pct=round(passed_count / total * 100, 1) if total else 0.0,
        results=results,
    )

@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    entries = _load_feedback(req.use_case)
    entries.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": req.query, "document_id": req.document_id,
        "relevant": req.relevant, "search_score": round(req.score, 4),
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

    if config.is_cosmosdb_use_case(use_case):
        try:
            docs = _list_cosmosdb_documents(use_case)
            return {"use_case": use_case, "total": len(docs), "documents": docs}
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Cosmos DB query failed for {use_case}: {exc}",
            )

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
        # For JSON files, extract key metadata
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


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: str, use_case: str = "engineering_docs"):
    """Get document content by ID (returns JSON structured data or text)."""
    if use_case not in _VALID_USE_CASES:
        raise HTTPException(status_code=400, detail=f"Invalid use_case: {use_case}")

    if config.is_cosmosdb_use_case(use_case):
        try:
            doc = _get_cosmosdb_document(doc_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Cosmos DB query failed: {exc}")

        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in Cosmos DB")

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

    data_dir = config.uc_data_dir(use_case)
    # Try JSON first (structured), then txt/pdf
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

@app.get("/api/documents/{doc_id}/pdf")
def get_document_pdf(doc_id: str, use_case: str = "engineering_docs"):
    """Serve the raw PDF file for in-browser viewing."""
    if use_case not in _VALID_USE_CASES:
        raise HTTPException(status_code=400, detail=f"Invalid use_case: {use_case}")
    data_dir = config.uc_data_dir(use_case)
    pdf_path = os.path.join(data_dir, f"{doc_id}.pdf")
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf", filename=f"{doc_id}.pdf")
    raise HTTPException(status_code=404, detail=f"PDF {doc_id}.pdf not found")
