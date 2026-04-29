"""Quick accuracy test using agent prompts from prompts_config.json.

Tests grounding rules:
- Response must not be empty
- Response must not be a fallback/not-found
- Response must cite at least one use-case document ID
- If prompt mentions a specific doc ID, that ID must appear in response

Set USE_CASE env var: engineering_docs (default) or filter_design
"""
import os, sys, re, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from azure.identity import DefaultAzureCredential
from scripts.create_agent import query_agent

USE_CASE = config.get_use_case()
DOC_PREFIX = "FD-TC" if USE_CASE == "filter_design" else "MFG-TC"
DOC_PATTERN = re.compile(rf"\b{DOC_PREFIX}-\d{{4}}\b", re.IGNORECASE)

FALLBACK_PHRASES = [
    "could not find relevant information",
    "no relevant information",
    "i don't have",
    "not found in",
    "no results found",
]

def is_fallback(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in FALLBACK_PHRASES)

def main():
    prompts_cfg = config.prompts_config()["use_cases"][USE_CASE]
    # Use the "agent" category prompts
    prompts = [p["text"] for p in prompts_cfg.get("agent", [])]
    if not prompts:
        print("No agent prompts found!")
        return

    print(f"=== Accuracy Test: {USE_CASE} ({len(prompts)} prompts) ===\n")
    cred = DefaultAzureCredential()

    passed = 0
    failed = 0
    results = []

    for i, prompt in enumerate(prompts, 1):
        print(f"[{i}/{len(prompts)}] {prompt[:80]}...")
        start = time.time()
        resp = query_agent(prompt, credential=cred) or ""
        elapsed = time.time() - start
        resp_clean = " ".join(resp.split())

        ok = True
        reason = "OK"

        if not resp_clean:
            ok, reason = False, "Empty response"
        elif is_fallback(resp_clean):
            ok, reason = False, "Fallback/not-found"
        elif not DOC_PATTERN.search(resp_clean):
            ok, reason = False, "No doc ID citation"
        else:
            # Check if prompt mentions a specific doc ID
            prompt_ids = [m.upper() for m in DOC_PATTERN.findall(prompt)]
            for pid in prompt_ids:
                if pid not in resp_clean.upper():
                    ok, reason = False, f"Missing cited doc: {pid}"
                    break

        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1

        results.append({"prompt": prompt, "status": status, "reason": reason,
                        "elapsed_s": round(elapsed, 1),
                        "response_preview": resp_clean[:200]})
        print(f"  {status} ({reason}) [{elapsed:.1f}s]")

    total = passed + failed
    accuracy = (passed / total * 100) if total else 0
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{total} passed = {accuracy:.1f}% accuracy")
    print(f"{'='*60}")

    if failed > 0:
        print(f"\nFailed prompts:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  [{r['reason']}] {r['prompt'][:80]}")
                print(f"    Response: {r['response_preview'][:120]}")

    # Save results
    out_path = os.path.join(config.uc_data_dir(), "accuracy_test_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"use_case": USE_CASE, "total": total, "passed": passed,
                    "failed": failed, "accuracy_pct": round(accuracy, 1),
                    "results": results}, f, indent=2)
    print(f"\nResults saved to {out_path}")

if __name__ == "__main__":
    main()
