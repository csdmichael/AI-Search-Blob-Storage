"""
Retest agent grounding accuracy using prompts from use-case demo scripts.

Rules used for this grounded test:
- Prompt list is parsed from use-cases/<use-case>/DEMO_SCRIPT.md table.
- Agent must provide a non-empty answer.
- Agent must not return the configured "not found" fallback.
- Agent must include at least one use-case document ID in the response.
- For prompts that mention a specific document ID, the same ID must appear in response.

Set USE_CASE env var to select: engineering_docs (default) or filter_design.
"""

import os
import re
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from azure.identity import DefaultAzureCredential
from scripts.create_agent import query_agent


@dataclass
class CaseResult:
    prompt: str
    passed: bool
    reason: str
    response_preview: str


def _demo_script_path(use_case: str) -> str:
    mapping = {
        "engineering_docs": os.path.join("use-cases", "engineering-docs", "DEMO_SCRIPT.md"),
        "filter_design": os.path.join("use-cases", "filter-design", "DEMO_SCRIPT.md"),
    }
    return os.path.join(config.PROJECT_ROOT, mapping[use_case])


def _parse_prompts(markdown_path: str) -> list[str]:
    prompts: list[str] = []
    pattern = re.compile(r"^\|\s*\d+\s*\|\s*\*\"(.+?)\"\*\s*\|", re.MULTILINE)
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()
    for m in pattern.finditer(content):
        prompts.append(m.group(1).strip())
    return prompts


def _fallback_detected(response: str) -> bool:
    text = response.lower()
    return (
        "could not find relevant information in the engineering documents index" in text
        or "could not find relevant information in the filter design documents index" in text
        or "no results found in the document index" in text
    )


def _expected_patterns(use_case: str):
    if use_case == "engineering_docs":
        return re.compile(r"\bMFG-TC-\d{4}\b"), re.compile(r"\bMFG-TC-\d{4}\b", re.IGNORECASE)
    return re.compile(r"\bFD-TC-\d{4}\b"), re.compile(r"\bFD-TC-\d{4}\b", re.IGNORECASE)


def evaluate_prompts(use_case: str, prompts: list[str]) -> list[CaseResult]:
    credential = DefaultAzureCredential()
    expected_in_answer, expected_in_prompt = _expected_patterns(use_case)

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

        if not expected_in_answer.search(response_compact):
            results.append(CaseResult(prompt, False, "no use-case document ID in answer", response_compact[:220]))
            continue

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

    prompts = _parse_prompts(demo_path)
    if not prompts:
        print(f"No prompts found in demo script: {demo_path}")
        return 1

    print(f"Use case: {use_case}")
    print(f"Demo script: {demo_path}")
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
