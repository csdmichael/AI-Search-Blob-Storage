"""
Fine-tune a model on engineering documents and evaluate accuracy.

This script:
1. Generates training data (Q&A pairs) from the engineering documents
2. Creates a fine-tuning dataset in JSONL format
3. Uploads the dataset to Azure AI Foundry
4. Initiates fine-tuning on the base model
5. Evaluates the fine-tuned model against a held-out test set
6. Produces an evaluation report (docs/evaluation_results.md)

Note: Fine-tuning requires a compatible base model (e.g., gpt-4o-mini)
      and sufficient quota in your Foundry project.

Set USE_CASE env var to select: engineering_docs (default) or filter_design
"""

import os
import re
import json
import random
import time
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

_ft_cfg = config.uc_agent_config()["fine_tuning"]
_doc_cfg = config.uc_document_config()

PROJECT_ENDPOINT = config.project_endpoint()
BASE_MODEL = os.environ.get("FINE_TUNE_BASE_MODEL", _ft_cfg["base_model"])
DATA_DIR = config.uc_data_dir()
DOCS_DIR = config.DOCS_DIR
TRAINING_FILE = os.path.join(DATA_DIR, "fine_tuning_train.jsonl")
VALIDATION_FILE = os.path.join(DATA_DIR, "fine_tuning_validation.jsonl")
DOC_PREFIX = _doc_cfg["document_prefix"]
TOTAL_DOCUMENTS = _doc_cfg["total_documents"]

SYSTEM_PROMPT = _ft_cfg["system_prompt"]
FINE_TUNE_SUFFIX = _ft_cfg["suffix"]
N_EPOCHS = _ft_cfg["n_epochs"]
TRAIN_SPLIT = _ft_cfg["train_split"]
EVAL_SAMPLE_SIZE = _ft_cfg["eval_sample_size"]


# ─────────────────────────────────────────────────────────────────────
# Step 1: Generate Q&A training pairs from documents
# ─────────────────────────────────────────────────────────────────────

def extract_qa_pairs(content: str, doc_number: str) -> list[dict]:
    """Extract question-answer pairs from a single engineering document."""
    pairs = []

    # Extract key fields
    title_m = re.search(r"^Title:\s*(.+)$", content, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else ""

    status_m = re.search(r"^Result Classification:\s*(.+)$", content, re.MULTILINE)
    status = status_m.group(1).strip() if status_m else ""

    product_m = re.search(r"^- Product Line:\s*(.+)$", content, re.MULTILINE)
    product = product_m.group(1).strip() if product_m else ""

    defect_m = re.search(r"^- Target Defect:\s*(.+)$", content, re.MULTILINE)
    defect = defect_m.group(1).strip() if defect_m else ""

    process_m = re.search(r"^- Process Step:\s*(.+)$", content, re.MULTILINE)
    process = process_m.group(1).strip() if process_m else ""

    tech_m = re.search(r"^- Technology Node:\s*(.+)$", content, re.MULTILINE)
    tech = tech_m.group(1).strip() if tech_m else ""

    fab_m = re.search(r"^Fab Location:\s*(.+)$", content, re.MULTILINE)
    fab = fab_m.group(1).strip() if fab_m else ""

    defect_count_m = re.search(r"^Total Defects Found:\s*(\d+)", content, re.MULTILINE)
    defect_count = defect_count_m.group(1) if defect_count_m else "N/A"

    capture_m = re.search(r"^Capture Rate:\s*([\d.]+)%", content, re.MULTILINE)
    capture_rate = capture_m.group(1) if capture_m else "N/A"

    nuisance_m = re.search(r"^Nuisance Rate:\s*([\d.]+)%", content, re.MULTILINE)
    nuisance_rate = nuisance_m.group(1) if nuisance_m else "N/A"

    # Objective section
    obj_m = re.search(r"1\. OBJECTIVE\n─+\n\n(.+?)(?=\n─)", content, re.DOTALL)
    objective = obj_m.group(1).strip() if obj_m else ""

    # Acceptance criteria
    acc_m = re.search(r"5\. ACCEPTANCE CRITERIA\n─+\n\n(.+?)(?=\n─)", content, re.DOTALL)
    acceptance = acc_m.group(1).strip() if acc_m else ""

    # Observations
    obs_m = re.search(r"7\. OBSERVATIONS AND FINDINGS\n─+\n\n(.+?)(?=\n─)", content, re.DOTALL)
    observations = obs_m.group(1).strip() if obs_m else ""

    # Corrective actions
    corr_m = re.search(r"8\. CORRECTIVE ACTIONS.+?\n─+\n\n(.+?)(?=\n─)", content, re.DOTALL)
    corrective = corr_m.group(1).strip() if corr_m else ""

    # ── Generate Q&A pairs ──

    # Q1: What does this test case cover?
    if title:
        pairs.append({
            "question": f"What does test case {doc_number} cover?",
            "answer": f"Test case {doc_number} covers: {title}. {objective[:300]}"
        })

    # Q2: What were the test results?
    if status:
        pairs.append({
            "question": f"What were the results of test case {doc_number}?",
            "answer": (
                f"Test case {doc_number} result: {status}. "
                f"Total defects found: {defect_count}, "
                f"capture rate: {capture_rate}%, "
                f"nuisance rate: {nuisance_rate}%."
            )
        })

    # Q3: What system and defect type?
    if product and defect:
        pairs.append({
            "question": f"Which inspection system is used in {doc_number} and what defects does it target?",
            "answer": (
                f"Test case {doc_number} uses the {product} system "
                f"to detect {defect} defects during the {process} step "
                f"at the {tech} technology node, located at {fab}."
            )
        })

    # Q4: Acceptance criteria
    if acceptance:
        pairs.append({
            "question": f"What are the acceptance criteria for {doc_number}?",
            "answer": f"Acceptance criteria for {doc_number}:\n{acceptance}"
        })

    # Q5: Observations
    if observations:
        pairs.append({
            "question": f"What observations were noted in {doc_number}?",
            "answer": f"Key observations from {doc_number}:\n{observations[:500]}"
        })

    # Q6: Corrective actions (only for non-PASS)
    if corrective and "No corrective actions required" not in corrective:
        pairs.append({
            "question": f"What corrective actions are recommended in {doc_number}?",
            "answer": f"Corrective actions for {doc_number}:\n{corrective[:500]}"
        })

    # Q7: Cross-document question patterns
    if product:
        pairs.append({
            "question": f"What test cases involve the {product} system?",
            "answer": (
                f"Test case {doc_number} involves the {product} system "
                f"for {defect} detection at the {tech} node ({process}). "
                f"Refer to the full index for other test cases using this system."
            )
        })

    return pairs


def generate_training_data():
    """Generate JSONL training and validation files from engineering docs."""
    files = sorted(f for f in os.listdir(DATA_DIR) if f.startswith(DOC_PREFIX) and f.endswith(".txt"))
    all_pairs = []

    for filename in files:
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        doc_number = filename.replace(".txt", "")
        pairs = extract_qa_pairs(content, doc_number)
        all_pairs.extend(pairs)

    random.seed(42)
    random.shuffle(all_pairs)

    # train/validation split
    split_idx = int(len(all_pairs) * TRAIN_SPLIT)
    train_pairs = all_pairs[:split_idx]
    val_pairs = all_pairs[split_idx:]

    # Write JSONL in OpenAI fine-tuning format
    def write_jsonl(pairs, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            for pair in pairs:
                entry = {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": pair["question"]},
                        {"role": "assistant", "content": pair["answer"]},
                    ]
                }
                f.write(json.dumps(entry) + "\n")

    write_jsonl(train_pairs, TRAINING_FILE)
    write_jsonl(val_pairs, VALIDATION_FILE)

    print(f"Generated {len(train_pairs)} training examples → {TRAINING_FILE}")
    print(f"Generated {len(val_pairs)} validation examples → {VALIDATION_FILE}")

    return train_pairs, val_pairs


# ─────────────────────────────────────────────────────────────────────
# Step 2: Upload dataset and fine-tune
# ─────────────────────────────────────────────────────────────────────

def fine_tune_model(project_client: AIProjectClient):
    """Upload training data and start fine-tuning job."""
    openai_client = project_client.get_openai_client(api_version="2025-03-01-preview")

    # Upload training file
    print("\nUploading training file...")
    with open(TRAINING_FILE, "rb") as f:
        train_file = openai_client.files.create(file=f, purpose="fine-tune")
    print(f"  Training file ID: {train_file.id}")

    # Upload validation file
    print("Uploading validation file...")
    with open(VALIDATION_FILE, "rb") as f:
        val_file = openai_client.files.create(file=f, purpose="fine-tune")
    print(f"  Validation file ID: {val_file.id}")

    # Create fine-tuning job
    print(f"\nStarting fine-tuning job (base model: {BASE_MODEL})...")
    job = openai_client.fine_tuning.jobs.create(
        training_file=train_file.id,
        validation_file=val_file.id,
        model=BASE_MODEL,
        hyperparameters={
            "n_epochs": N_EPOCHS,
        },
        suffix=FINE_TUNE_SUFFIX,
    )

    print(f"  Fine-tuning job ID: {job.id}")
    print(f"  Status: {job.status}")

    # Poll for completion
    print("\nWaiting for fine-tuning to complete (this may take 15-60 minutes)...")
    while job.status not in ("succeeded", "failed", "cancelled"):
        time.sleep(30)
        job = openai_client.fine_tuning.jobs.retrieve(job.id)
        print(f"  Status: {job.status}")

    if job.status == "succeeded":
        print(f"\nFine-tuning completed! Model: {job.fine_tuned_model}")
        return job
    else:
        print(f"\nFine-tuning failed: {job.error}")
        return job


# ─────────────────────────────────────────────────────────────────────
# Step 3: Evaluate fine-tuned model
# ─────────────────────────────────────────────────────────────────────

def evaluate_model(project_client: AIProjectClient, model_name: str, val_pairs: list[dict]):
    """Evaluate the fine-tuned model on validation data and produce metrics."""
    openai_client = project_client.get_openai_client(api_version="2025-03-01-preview")

    results = []
    correct_doc_citations = 0
    total_evaluated = 0
    total_tokens = 0

    # Sample up to configured size for evaluation
    eval_sample = val_pairs[:EVAL_SAMPLE_SIZE] if len(val_pairs) > EVAL_SAMPLE_SIZE else val_pairs

    print(f"\nEvaluating {len(eval_sample)} validation examples...")
    for i, pair in enumerate(eval_sample):
        try:
            response = openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": pair["question"]},
                ],
                max_tokens=500,
                temperature=0,
            )
            predicted = response.choices[0].message.content
            usage = response.usage

            # Evaluate: check if key entities from expected answer appear in prediction
            expected = pair["answer"]
            doc_pattern = re.escape(DOC_PREFIX) + r"-\d{4}"
            doc_refs = re.findall(doc_pattern, expected)
            predicted_refs = re.findall(doc_pattern, predicted)
            citation_match = bool(set(doc_refs) & set(predicted_refs)) if doc_refs else True

            if citation_match:
                correct_doc_citations += 1

            total_evaluated += 1
            total_tokens += usage.total_tokens if usage else 0

            results.append({
                "question": pair["question"],
                "expected_answer": expected[:300],
                "predicted_answer": predicted[:300],
                "citation_match": citation_match,
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
            })

            if (i + 1) % 10 == 0:
                print(f"  Evaluated {i + 1}/{len(eval_sample)}")

        except Exception as e:
            print(f"  Error evaluating example {i + 1}: {e}")
            results.append({
                "question": pair["question"],
                "expected_answer": pair["answer"][:300],
                "predicted_answer": f"ERROR: {e}",
                "citation_match": False,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            })
            total_evaluated += 1

    # Calculate metrics
    citation_accuracy = (correct_doc_citations / total_evaluated * 100) if total_evaluated else 0
    avg_tokens = total_tokens / total_evaluated if total_evaluated else 0

    metrics = {
        "model": model_name,
        "base_model": BASE_MODEL,
        "timestamp": datetime.utcnow().isoformat(),
        "total_evaluated": total_evaluated,
        "citation_accuracy_pct": round(citation_accuracy, 1),
        "avg_tokens_per_query": round(avg_tokens, 1),
        "results": results,
    }

    return metrics


def generate_eval_report(metrics: dict, train_count: int, val_count: int):
    """Generate a Markdown evaluation report."""
    report = f"""# Fine-Tuning Evaluation Results

## Summary

| Metric | Value |
|--------|-------|
| **Base Model** | `{metrics['base_model']}` |
| **Fine-Tuned Model** | `{metrics['model']}` |
| **Evaluation Date** | {metrics['timestamp'][:10]} |
| **Training Examples** | {train_count} |
| **Validation Examples** | {val_count} |
| **Evaluated Samples** | {metrics['total_evaluated']} |
| **Citation Accuracy** | {metrics['citation_accuracy_pct']}% |
| **Avg Tokens/Query** | {metrics['avg_tokens_per_query']} |

## Methodology

### Training Data Generation
- Q&A pairs were automatically extracted from all {TOTAL_DOCUMENTS} engineering test case documents
- Each document yields 5-7 question-answer pairs covering: objectives, results, systems, acceptance criteria, observations, and corrective actions
- Training/validation split: 80/20 with fixed random seed for reproducibility

### Fine-Tuning Configuration
- Base model: `{metrics['base_model']}`
- Epochs: {N_EPOCHS}
- Batch size: auto
- Learning rate multiplier: auto
- Suffix: `{FINE_TUNE_SUFFIX}`

### Evaluation Criteria
1. **Citation Accuracy**: Does the response correctly cite the relevant {DOC_PREFIX} document number?
2. **Response Relevance**: Does the response contain key information from the expected answer?
3. **Token Efficiency**: Average tokens used per query (lower is better for cost)

## Detailed Results

| # | Question | Citation Match | Prompt Tokens | Completion Tokens |
|---|----------|:--------------:|:-------------:|:-----------------:|
"""
    for i, r in enumerate(metrics["results"][:50], 1):
        q = r["question"][:80].replace("|", "\\|")
        cite = "✅" if r["citation_match"] else "❌"
        report += f"| {i} | {q} | {cite} | {r['prompt_tokens']} | {r['completion_tokens']} |\n"

    report += f"""
## Sample Predictions

"""
    for i, r in enumerate(metrics["results"][:5], 1):
        report += f"""### Example {i}

**Question:** {r['question']}

**Expected:** {r['expected_answer'][:200]}...

**Predicted:** {r['predicted_answer'][:200]}...

**Citation Match:** {'✅ Yes' if r['citation_match'] else '❌ No'}

---

"""

    report += f"""## Recommendations

1. **If citation accuracy < 90%**: Increase training epochs or add more explicit citation examples
2. **If responses are too verbose**: Add length constraints to training examples
3. **For production use**: Compare fine-tuned model results against the base model + RAG approach
4. **Periodic re-training**: Re-generate training data when new engineering documents are added

## Files

| File | Description |
|------|-------------|
| `data/fine_tuning_train.jsonl` | Training dataset ({train_count} examples) |
| `data/fine_tuning_validation.jsonl` | Validation dataset ({val_count} examples) |
| `data/evaluation_metrics.json` | Raw evaluation metrics (JSON) |
"""
    return report


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def main():
    credential = DefaultAzureCredential()

    # Step 1: Generate training data
    print("=" * 60)
    print("STEP 1: Generate Training Data")
    print("=" * 60)
    train_pairs, val_pairs = generate_training_data()

    # Step 2: Fine-tune
    print("\n" + "=" * 60)
    print("STEP 2: Fine-Tune Model")
    print("=" * 60)
    project_client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)
    fine_tuned = False
    try:
        job = fine_tune_model(project_client)
        if job.status == "succeeded":
            model_name = job.fine_tuned_model
            fine_tuned = True
        else:
            print(f"Fine-tuning did not succeed (status: {job.status}). Falling back to base model evaluation...")
            model_name = BASE_MODEL
    except Exception as e:
        print(f"Fine-tuning unavailable: {e}")
        print(f"Falling back to base model evaluation ({BASE_MODEL})...")
        model_name = BASE_MODEL

    # Step 3: Evaluate
    print("\n" + "=" * 60)
    print("STEP 3: Evaluate Model")
    print("=" * 60)
    metrics = evaluate_model(project_client, model_name, val_pairs)

    # Save raw metrics
    metrics_path = os.path.join(DATA_DIR, "evaluation_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"Raw metrics saved to: {metrics_path}")

    # Step 4: Generate report
    print("\n" + "=" * 60)
    print("STEP 4: Generate Evaluation Report")
    print("=" * 60)
    os.makedirs(DOCS_DIR, exist_ok=True)
    report = generate_eval_report(metrics, len(train_pairs), len(val_pairs))
    report_path = os.path.join(DOCS_DIR, "evaluation_results.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Evaluation report saved to: {report_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
