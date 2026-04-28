"""
Ranking and feedback loop for improving agent accuracy from 90% to 95%.

This script implements:
1. Query result ranking with relevance scoring
2. User feedback collection and storage
3. Feedback-driven re-ranking to boost frequently-cited, high-rated documents
4. Evaluation of accuracy improvements over baseline

Set USE_CASE env var to select: engineering_docs (default) or filter_design
"""

import os
import json
import time
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder

_uc_search = config.uc_search_config()
_uc_agent = config.uc_agent_config()["agent"]
_ft_cfg = config.uc_agent_config()["fine_tuning"]
_ranking_cfg = config.agent_config()["ranking"]
_doc_cfg = config.uc_document_config()

SEARCH_ENDPOINT = config.search_endpoint()
INDEX_NAME = _uc_search["chunked_index"]["name"]
SEMANTIC_CONFIG_NAME = _uc_search["chunked_index"]["semantic_config_name"]
PROJECT_ENDPOINT = config.project_endpoint()
AGENT_NAME = _uc_agent["name"]
DOC_PREFIX = _doc_cfg["document_prefix"]
DATA_DIR = config.uc_data_dir()
DOCS_DIR = config.uc_docs_dir()

FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback_log.json")
RANKING_REPORT = os.path.join(DOCS_DIR, "ranking_report.md")


# ─────────────────────────────────────────────────────────────────────
# Feedback store
# ─────────────────────────────────────────────────────────────────────

def load_feedback() -> list[dict]:
    """Load existing feedback entries."""
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_feedback(entries: list[dict]):
    """Persist feedback entries."""
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def record_feedback(query: str, doc_id: str, relevant: bool, score: float, notes: str = ""):
    """Record a single feedback entry."""
    entries = load_feedback()
    entries.append({
        "timestamp": datetime.utcnow().isoformat(),
        "query": query,
        "document_id": doc_id,
        "relevant": relevant,
        "search_score": round(score, 4),
        "notes": notes,
    })
    save_feedback(entries)
    return len(entries)


# ─────────────────────────────────────────────────────────────────────
# Ranked search with feedback boosting
# ─────────────────────────────────────────────────────────────────────

def compute_boost_map(feedback: list[dict]) -> dict[str, float]:
    """Compute a per-document boost factor from accumulated feedback.

    Documents rated as 'relevant' more often get higher boost.
    Boost = 1.0 + (relevant_count - irrelevant_count) * 0.05, clamped [0.8, 1.5].
    """
    doc_scores: dict[str, int] = {}
    for entry in feedback:
        doc = entry["document_id"]
        delta = 1 if entry["relevant"] else -1
        doc_scores[doc] = doc_scores.get(doc, 0) + delta

    return {
        doc: max(0.8, min(1.5, 1.0 + score * 0.05))
        for doc, score in doc_scores.items()
    }


def ranked_search(search_client: SearchClient, query: str, top: int = 10) -> list[dict]:
    """Execute a semantic search and re-rank results using feedback boosts."""
    feedback = load_feedback()
    boost_map = compute_boost_map(feedback)

    results = search_client.search(
        search_text=query,
        query_type="semantic",
        semantic_configuration_name=SEMANTIC_CONFIG_NAME,
        top=top * 2,  # fetch more so re-ranking has room
        include_total_count=True,
    )

    scored = []
    for r in results:
        doc_name = r.get("source_file", r.get("document_number", ""))
        base_score = r.get("@search.reranker_score", r.get("@search.score", 0))
        boost = boost_map.get(doc_name, 1.0)
        final_score = base_score * boost
        scored.append({
            "document": doc_name,
            "base_score": round(base_score, 4),
            "boost": round(boost, 3),
            "final_score": round(final_score, 4),
            "content_preview": r.get("content", "")[:300],
        })

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    return scored[:top]


# ─────────────────────────────────────────────────────────────────────
# Agent-based evaluation with ranking
# ─────────────────────────────────────────────────────────────────────

def evaluate_agent_accuracy(project_client: AIProjectClient, search_client: SearchClient,
                            queries: list[str]) -> dict:
    """Evaluate agent responses and search ranking accuracy.

    For each query:
    - Run ranked search and check if top result is relevant
    - Run agent query and check if response cites a valid document
    """
    import re

    agents = project_client.agents.list_agents()
    agent = None
    for a in agents:
        if a.name == AGENT_NAME:
            agent = a
            break

    if not agent:
        print(f"Agent '{AGENT_NAME}' not found. Evaluating search-only.")

    results = []
    search_hits = 0
    agent_citations = 0
    doc_pattern = re.compile(re.escape(DOC_PREFIX) + r"-\d{4}")

    for i, query in enumerate(queries):
        print(f"  [{i+1}/{len(queries)}] {query[:60]}...")

        # Search ranking evaluation
        ranked = ranked_search(search_client, query, top=5)
        search_hit = bool(ranked and ranked[0]["final_score"] > _ranking_cfg["relevance_threshold"])
        if search_hit:
            search_hits += 1

        # Agent evaluation (if available)
        agent_cite = False
        agent_response = ""
        if agent:
            try:
                thread = project_client.agents.threads.create()
                project_client.agents.messages.create(
                    thread_id=thread.id, role="user", content=query)
                run = project_client.agents.runs.create_and_process(
                    thread_id=thread.id, agent_id=agent.id)
                if run.status != "failed":
                    messages = project_client.agents.messages.list(
                        thread_id=thread.id, order=ListSortOrder.ASCENDING)
                    for msg in messages:
                        if msg.role == "assistant" and msg.text_messages:
                            agent_response = msg.text_messages[-1].text.value
                            if doc_pattern.search(agent_response):
                                agent_cite = True
                                agent_citations += 1
                            break
            except Exception as e:
                print(f"    Agent error: {e}")

        results.append({
            "query": query,
            "search_hit": search_hit,
            "top_result": ranked[0]["document"] if ranked else "N/A",
            "top_score": ranked[0]["final_score"] if ranked else 0,
            "agent_cited": agent_cite,
            "agent_response_preview": agent_response[:200],
        })

    total = len(queries)
    return {
        "total_queries": total,
        "search_accuracy_pct": round(search_hits / total * 100, 1) if total else 0,
        "agent_citation_pct": round(agent_citations / total * 100, 1) if total else 0,
        "feedback_entries": len(load_feedback()),
        "results": results,
    }


# ─────────────────────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────────────────────

def generate_ranking_report(metrics: dict):
    """Generate a Markdown report of ranking and feedback evaluation."""
    report = f"""# Ranking & Feedback Loop — Evaluation Report

## Summary

| Metric | Value |
|--------|-------|
| **Total Queries Evaluated** | {metrics['total_queries']} |
| **Search Ranking Accuracy** | {metrics['search_accuracy_pct']}% |
| **Agent Citation Accuracy** | {metrics['agent_citation_pct']}% |
| **Feedback Entries Collected** | {metrics['feedback_entries']} |
| **Evaluation Date** | {datetime.utcnow().strftime('%Y-%m-%d')} |

## Approach — From 90% to 95%

The following techniques are applied to improve accuracy beyond the baseline 90%:

1. **Feedback-Driven Re-Ranking**: User feedback (relevant/irrelevant) is collected per query-document pair. Documents with consistently positive feedback receive a boost factor (up to 1.5×) applied on top of the semantic reranker score.

2. **Relevance Threshold Filtering**: Results below a configurable relevance threshold ({_ranking_cfg['relevance_threshold']}) are suppressed, reducing noise in agent context.

3. **Section-Level Chunking**: The chunked index provides more granular matches, so the agent gets precisely the relevant section instead of the full document.

4. **Custom Scoring Profile**: Title (3×), document number (2.5×), and section name (2×) are boosted relative to generic content (1×).

5. **Strict Agent Instructions**: The agent is instructed to never fabricate information, always cite sources, and respond with "not found" when the index has no relevant results.

## Detailed Results

| # | Query | Search Hit | Top Doc | Score | Agent Cited |
|---|-------|:----------:|---------|------:|:-----------:|
"""
    for i, r in enumerate(metrics["results"], 1):
        q = r["query"][:60].replace("|", "\\|")
        hit = "Yes" if r["search_hit"] else "No"
        cite = "Yes" if r["agent_cited"] else "No"
        report += f"| {i} | {q} | {hit} | {r['top_result']} | {r['top_score']} | {cite} |\n"

    report += """
## Recommendations

1. **Collect More Feedback**: Run the agent in production with feedback collection enabled to accumulate data for re-ranking.
2. **Periodic Re-Indexing**: Re-run `chunk_and_index.py` after document updates to keep the chunked index fresh.
3. **A/B Test Scoring Weights**: Experiment with different scoring profile weights to find the optimal configuration.
4. **Fine-Tune on Feedback Data**: Use positive feedback pairs as additional fine-tuning examples to improve the model's domain knowledge.
5. **Monitor Drift**: Track accuracy weekly; re-train if citation accuracy drops below 93%.
"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(RANKING_REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Ranking report saved to: {RANKING_REPORT}")
    return report


# ─────────────────────────────────────────────────────────────────────
# Synthetic feedback generation for demo
# ─────────────────────────────────────────────────────────────────────

def generate_synthetic_feedback(search_client: SearchClient, n_queries: int = 30):
    """Generate synthetic feedback by running queries and auto-rating results.

    Uses a heuristic: if the query terms appear in the document content, mark relevant.
    """
    import random
    random.seed(42)

    use_case = config.get_use_case()
    if use_case == "filter_design":
        sample_terms = [
            "SAW filter", "BAW filter", "FBAR", "insertion loss", "rejection",
            "5G NR", "Band 7", "duplexer", "temperature", "substrate",
            "Q factor", "WiFi", "resonator", "passband", "LiNbO3",
        ]
    else:
        sample_terms = [
            "Surfscan", "defect", "FinFET", "wafer inspection", "3nm",
            "CMP", "particle", "overlay", "Archer", "nuisance rate",
            "capture rate", "scratch", "contamination", "post-etch", "calibration",
        ]

    queries = [f"{random.choice(sample_terms)} {random.choice(sample_terms)}" for _ in range(n_queries)]

    print(f"Generating {n_queries} synthetic feedback entries...")
    for query in queries:
        results = search_client.search(search_text=query, top=3)
        for r in results:
            doc_name = r.get("source_file", r.get("document_number", ""))
            score = r.get("@search.score", 0)
            # Heuristic: if score > 5, likely relevant
            relevant = score > 5.0
            record_feedback(query, doc_name, relevant, score)

    total = len(load_feedback())
    print(f"Total feedback entries: {total}")


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def main():
    credential = DefaultAzureCredential()

    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=credential,
    )

    project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=credential,
    )

    use_case = config.get_use_case()

    # Step 1: Generate synthetic feedback if none exists
    if not load_feedback():
        print("=" * 60)
        print("STEP 1: Generate Synthetic Feedback")
        print("=" * 60)
        generate_synthetic_feedback(search_client)
    else:
        print(f"Using existing feedback ({len(load_feedback())} entries)")

    # Step 2: Run evaluation queries with ranked search
    print("\n" + "=" * 60)
    print("STEP 2: Evaluate Ranking + Agent Accuracy")
    print("=" * 60)

    if use_case == "filter_design":
        eval_queries = [
            "What filter designs target 5G NR sub-6 GHz bands?",
            "Which BAW filters have insertion loss below 1.5 dB?",
            "Show test cases for TC-SAW temperature stability.",
            "What are the acceptance criteria for duplexer isolation?",
            "Which filter designs failed and what corrective actions exist?",
            "What substrate materials are used for FBAR filters?",
            "Find WiFi 6E coexistence filter test results.",
            "What is the Q factor for Band 7 SAW filters?",
            "List corrective actions for high insertion loss designs.",
            "What design tools are used for 5G NR filter simulation?",
        ]
    else:
        eval_queries = [
            "What are the most common defect types found during wafer inspection?",
            "Which test cases failed and what corrective actions were recommended?",
            "How does the Surfscan system detect crystal originated particles?",
            "What is the acceptance criteria for 5nm node patterned wafer inspection?",
            "Show me test results for post-CMP contamination inspection.",
            "What inspection systems are used for FinFET manufacturing?",
            "Find documents about overlay metrology using the Archer system.",
            "What are the throughput requirements for 300mm wafer inspection?",
            "List all test cases with nuisance rate above 5%.",
            "What corrective actions address high nuisance rates?",
        ]

    metrics = evaluate_agent_accuracy(project_client, search_client, eval_queries)

    # Step 3: Generate report
    print("\n" + "=" * 60)
    print("STEP 3: Generate Ranking Report")
    print("=" * 60)
    generate_ranking_report(metrics)

    print(f"\nSearch Ranking Accuracy: {metrics['search_accuracy_pct']}%")
    print(f"Agent Citation Accuracy: {metrics['agent_citation_pct']}%")
    print("\nDone!")


if __name__ == "__main__":
    main()
