"""
Retest agent grounding accuracy using prompts from use-case demo scripts.

Rules used for this grounded test:
- Prompt list is parsed from use-cases/<use-case>/DEMO_SCRIPT.md table.
- For Cosmos DB use cases without DEMO_SCRIPT.md, uses agent prompts from prompts_config.json.
- Agent must provide a non-empty answer.
- Agent must not return the configured "not found" fallback.
- Agent must include at least one document citation in the response.
- For blob storage use cases, citation must contain a use-case document ID.
- For prompts that mention a specific document ID, the same ID must appear in response.

Set USE_CASE env var to select: engineering_docs, filter_design, tax_pdf_forms, eng_design_ppt.
"""

import os
import re
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from azure.identity import DefaultAzureCredential
from scripts.create_agent import query_agent

# Universal annotation pattern: [source†index]
_ANNOTATION_PATTERN = re.compile(r"\[([^\[\]†]+?)†([^\[\]]+?)\]")


@dataclass
class CaseResult:
    prompt: str
    passed: bool
    reason: str
    response_preview: str


def _demo_script_path(use_case: str) -> str | None:
    mapping = {
        "engineering_docs": os.path.join("use-cases", "engineering-docs", "DEMO_SCRIPT.md"),
        "filter_design": os.path.join("use-cases", "filter-design", "DEMO_SCRIPT.md"),
        "tax_pdf_forms": os.path.join("use-cases", "tax-pdf-forms", "DEMO_SCRIPT.md"),
        "eng_design_ppt": os.path.join("use-cases", "eng-design-ppt", "DEMO_SCRIPT.md"),
    }
    path = os.path.join(config.PROJECT_ROOT, mapping[use_case])
    return path if os.path.exists(path) else None


def _parse_prompts(markdown_path: str) -> list[str]:
    prompts: list[str] = []
    pattern = re.compile(r"^\|\s*\d+\s*\|\s*\*\"(.+?)\"\*\s*\|", re.MULTILINE)
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()
    for m in pattern.finditer(content):
        prompts.append(m.group(1).strip())
    return prompts


def _load_prompts_from_config(use_case: str) -> list[str]:
    """Fallback: load agent prompts from prompts_config.json."""
    prompts_cfg = config.prompts_config()["use_cases"][use_case]
    return [p["text"] for p in prompts_cfg.get("agent", [])]


def _fallback_detected(response: str) -> bool:
    text = response.lower()
    fallback_phrases = [
        "could not find relevant information",
        "no results found in the document index",
        "no relevant information",
        "i don't have",
        "not found in",
    ]
    return any(p in text for p in fallback_phrases)


def _expected_patterns(use_case: str):
    if use_case == "engineering_docs":
        return re.compile(r"\bMFG-TC-\d{4}\b"), re.compile(r"\bMFG-TC-\d{4}\b", re.IGNORECASE)
    if use_case == "filter_design":
        return re.compile(r"\bFD-TC-\d{4}\b"), re.compile(r"\bFD-TC-\d{4}\b", re.IGNORECASE)
    # Cosmos DB use cases: no prefix-based doc ID pattern
    return None, None


def evaluate_prompts(use_case: str, prompts: list[str]) -> list[CaseResult]:
    credential = DefaultAzureCredential()
    expected_in_answer, expected_in_prompt = _expected_patterns(use_case)
    is_cosmosdb = config.is_cosmosdb_use_case(use_case)

    results: list[CaseResult] = []
    for prompt in prompts:
        response = query_agent(prompt, credential=credential) or ""
        response_compact = " ".join(response.split())

        if not response_compact:
            results.append(CaseResult(prompt, False, "empty response", ""))
            continue

        if _fallback_detected(response_compact):
            results.append(CaseResult(prompt, False, "fallback/not-found response", response_compact[:220]))
            continue

        if is_cosmosdb:
            # For Cosmos DB use cases, check for any [source†index] annotation
            if not _ANNOTATION_PATTERN.search(response_compact):
                results.append(CaseResult(prompt, False, "no document citation in answer", response_compact[:220]))
                continue
        else:
            # For blob storage use cases, check for prefix-based doc ID
            if expected_in_answer and not expected_in_answer.search(response_compact):
                results.append(CaseResult(prompt, False, "no use-case document ID in answer", response_compact[:220]))
                continue

            if expected_in_prompt:
                specific = expected_in_prompt.search(prompt)
                if specific:
                    specific_id = specific.group(0).upper()
                    if specific_id not in response_compact.upper():
                        results.append(CaseResult(prompt, False, f"specific doc ID missing in answer: {specific_id}", response_compact[:220]))
                        continue

        results.append(CaseResult(prompt, True, "ok", response_compact[:220]))

    return results


def main():
    use_case = config.get_use_case()
    demo_path = _demo_script_path(use_case)

    if demo_path:
        prompts = _parse_prompts(demo_path)
        source_label = f"Demo script: {demo_path}"
    else:
        prompts = _load_prompts_from_config(use_case)
        source_label = "Agent prompts from prompts_config.json"

    if not prompts:
        print(f"No prompts found for use case: {use_case}")
        return 1

    print(f"Use case: {use_case}")
    print(f"Source: {source_label}")
    print(f"Prompts parsed: {len(prompts)}")
    print("-" * 80)

    results = evaluate_prompts(use_case, prompts)
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    accuracy = (passed / total) * 100 if total else 0.0

    for i, result in enumerate(results, 1):
        status = "PASS" if result.passed else "FAIL"
        print(f"[{i:02d}] {status} - {result.prompt}")
        if not result.passed:
            print(f"     reason: {result.reason}")
            if result.response_preview:
                print(f"     preview: {result.response_preview}")

    print("-" * 80)
    print(f"ACCURACY: {passed}/{total} = {accuracy:.1f}%")

    threshold = 90.0
    if accuracy > threshold:
        print("RESULT: PASS (accuracy is over 90%)")
        return 0

    print("RESULT: FAIL (accuracy is not over 90%)")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
