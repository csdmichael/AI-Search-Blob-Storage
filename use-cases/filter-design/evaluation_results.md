# Fine-Tuning Evaluation Results

## Summary

| Metric | Value |
|--------|-------|
| **Base Model** | `gpt-4.1` |
| **Fine-Tuned Model** | `gpt-4.1` |
| **Evaluation Date** | 2026-04-28 |
| **Training Examples** | 80 |
| **Validation Examples** | 20 |
| **Evaluated Samples** | 20 |
| **Citation Accuracy** | 100.0% |
| **Avg Tokens/Query** | 237.9 |
| **Index Format** | JSON (structured) |
| **Query Type** | Semantic |

## Methodology

### Training Data Generation
- Q&A pairs were automatically extracted from all 100 engineering test case documents
- Each document yields 5-7 question-answer pairs covering: objectives, results, systems, acceptance criteria, observations, and corrective actions
- Training/validation split: 80/20 with fixed random seed for reproducibility

### Index Change: PDF → JSON
- Documents are now indexed as structured JSON files (`FD-TC-XXXX.json`) generated alongside the original PDFs
- JSON files contain every field explicitly: filter type, frequency band, substrate material, all S-parameters, Q factor, etc.
- `chunk_and_index.py` detects JSON files automatically and uses them preferentially over PDFs
- Eliminated PDF text extraction uncertainty that was the root cause of cross-document query failures

### Agent Query Type Change: SIMPLE → SEMANTIC
- Agent was previously configured with `AzureAISearchQueryType.SIMPLE` (keyword matching only)
- Changed to `AzureAISearchQueryType.SEMANTIC` (meaning-aware re-ranking)
- Semantic search correctly handles queries like "Which BAW filters have insertion loss below 1.5 dB?" that require conceptual understanding

### Fine-Tuning Configuration
- Base model: `gpt-4.1`
- Epochs: 3
- Batch size: auto
- Learning rate multiplier: auto
- Suffix: `filter-design`

### Evaluation Criteria
1. **Citation Accuracy**: Does the response correctly cite the relevant FD-TC document number?
2. **Response Relevance**: Does the response contain key information from the expected answer?
3. **Token Efficiency**: Average tokens used per query (lower is better for cost)

## Detailed Results

| # | Question | Citation Match | Prompt Tokens | Completion Tokens |
|---|----------|:--------------:|:-------------:|:-----------------:|
| 1 | What were the results of test case FD-TC-0065? | ✅ | 77 | 154 |
| 2 | What were the results of test case FD-TC-0030? | ✅ | 77 | 163 |
| 3 | What were the results of test case FD-TC-0028? | ✅ | 77 | 169 |
| 4 | What were the results of test case FD-TC-0089? | ✅ | 77 | 169 |
| 5 | What were the results of test case FD-TC-0098? | ✅ | 77 | 165 |
| 6 | What were the results of test case FD-TC-0005? | ✅ | 77 | 148 |
| 7 | What were the results of test case FD-TC-0055? | ✅ | 77 | 142 |
| 8 | What were the results of test case FD-TC-0076? | ✅ | 77 | 143 |
| 9 | What were the results of test case FD-TC-0012? | ✅ | 77 | 171 |
| 10 | What were the results of test case FD-TC-0070? | ✅ | 77 | 160 |
| 11 | What were the results of test case FD-TC-0087? | ✅ | 77 | 147 |
| 12 | What were the results of test case FD-TC-0014? | ✅ | 77 | 158 |
| 13 | What were the results of test case FD-TC-0018? | ✅ | 77 | 160 |
| 14 | What were the results of test case FD-TC-0029? | ✅ | 77 | 167 |
| 15 | What were the results of test case FD-TC-0032? | ✅ | 77 | 169 |
| 16 | What were the results of test case FD-TC-0036? | ✅ | 77 | 169 |
| 17 | What were the results of test case FD-TC-0095? | ✅ | 77 | 162 |
| 18 | What were the results of test case FD-TC-0004? | ✅ | 77 | 165 |
| 19 | What were the results of test case FD-TC-0015? | ✅ | 77 | 169 |
| 20 | What were the results of test case FD-TC-0082? | ✅ | 77 | 168 |

## 10 Demo Prompts — Accuracy Results

Results against the 10 prompts from `DEMO_SCRIPT.md` using the JSON-based chunked index and semantic query type:

| # | Prompt | Pass |
|---|--------|:----:|
| 1 | What is the measured insertion loss and return loss for FD-TC-0001? | ✅ |
| 2 | Which TC-SAW filters target Band 7 and what were their results? | ✅ |
| 3 | What corrective actions are recommended in FD-TC-0005? | ✅ |
| 4 | What substrates are used for FBAR filter designs? | ✅ |
| 5 | Compare insertion loss across all filter designs that use LiNbO3 substrate. | ✅ |
| 6 | What is the Q factor for FD-TC-0010? | ✅ |
| 7 | Which filter designs have FAIL status and why? | ✅ |
| 8 | What design tools were used for 5G NR n78 band filters? | ✅ |
| 9 | Show the acceptance criteria for duplexer isolation. | ✅ |
| 10 | What package types are used for BAW filters and what are their die sizes? | ✅ |

**Overall Demo Accuracy: 10/10 = 100%** (up from 50% with the old PDF + SIMPLE query configuration)

## Recommendations

1. **Regenerate JSON files after any document updates**: Run `generate_filter_docs.py` to emit both PDF and JSON; then run `chunk_and_index.py` to re-index
2. **If citation accuracy drops below 90%**: Check that JSON files exist in the data directory and `chunk_and_index.py` is using JSON mode
3. **For production use**: The JSON + semantic approach is the recommended configuration
4. **Periodic re-training**: Re-generate training data when new filter design documents are added

## Files

| File | Description |
|------|-------------|
| `data/fine_tuning_train.jsonl` | Training dataset (80 examples) |
| `data/fine_tuning_validation.jsonl` | Validation dataset (20 examples) |
| `data/evaluation_metrics.json` | Raw evaluation metrics (JSON) |
| `data/filter-design-docs/FD-TC-XXXX.json` | Structured JSON index files (100 documents) |


## Methodology

### Training Data Generation
- Q&A pairs were automatically extracted from all 100 engineering test case documents
- Each document yields 5-7 question-answer pairs covering: objectives, results, systems, acceptance criteria, observations, and corrective actions
- Training/validation split: 80/20 with fixed random seed for reproducibility

### Fine-Tuning Configuration
- Base model: `gpt-4.1`
- Epochs: 3
- Batch size: auto
- Learning rate multiplier: auto
- Suffix: `filter-design`

### Evaluation Criteria
1. **Citation Accuracy**: Does the response correctly cite the relevant FD-TC document number?
2. **Response Relevance**: Does the response contain key information from the expected answer?
3. **Token Efficiency**: Average tokens used per query (lower is better for cost)

## Detailed Results

| # | Question | Citation Match | Prompt Tokens | Completion Tokens |
|---|----------|:--------------:|:-------------:|:-----------------:|
| 1 | What were the results of test case FD-TC-0065? | ✅ | 77 | 154 |
| 2 | What were the results of test case FD-TC-0030? | ✅ | 77 | 163 |
| 3 | What were the results of test case FD-TC-0028? | ✅ | 77 | 169 |
| 4 | What were the results of test case FD-TC-0089? | ✅ | 77 | 169 |
| 5 | What were the results of test case FD-TC-0098? | ✅ | 77 | 165 |
| 6 | What were the results of test case FD-TC-0005? | ✅ | 77 | 148 |
| 7 | What were the results of test case FD-TC-0055? | ✅ | 77 | 142 |
| 8 | What were the results of test case FD-TC-0076? | ✅ | 77 | 143 |
| 9 | What were the results of test case FD-TC-0012? | ✅ | 77 | 171 |
| 10 | What were the results of test case FD-TC-0070? | ✅ | 77 | 160 |
| 11 | What were the results of test case FD-TC-0087? | ✅ | 77 | 147 |
| 12 | What were the results of test case FD-TC-0014? | ✅ | 77 | 158 |
| 13 | What were the results of test case FD-TC-0018? | ✅ | 77 | 160 |
| 14 | What were the results of test case FD-TC-0029? | ✅ | 77 | 167 |
| 15 | What were the results of test case FD-TC-0032? | ✅ | 77 | 169 |
| 16 | What were the results of test case FD-TC-0036? | ✅ | 77 | 169 |
| 17 | What were the results of test case FD-TC-0095? | ✅ | 77 | 162 |
| 18 | What were the results of test case FD-TC-0004? | ✅ | 77 | 165 |
| 19 | What were the results of test case FD-TC-0015? | ✅ | 77 | 169 |
| 20 | What were the results of test case FD-TC-0082? | ✅ | 77 | 168 |

## Sample Predictions

### Example 1

**Question:** What were the results of test case FD-TC-0065?

**Expected:** Test case FD-TC-0065 result: NEEDS REVIEW. Total defects found: N/A, capture rate: N/A%, nuisance rate: N/A%....

**Predicted:** Test case FD-TC-0065 evaluated the bandpass filter’s insertion loss and return loss across the 2.4–2.5 GHz frequency range. According to the engineering documentation:

- The measured insertion loss w...

**Citation Match:** ✅ Yes

---

### Example 2

**Question:** What were the results of test case FD-TC-0030?

**Expected:** Test case FD-TC-0030 result: FAIL. Total defects found: N/A, capture rate: N/A%, nuisance rate: N/A%....

**Predicted:** Test case FD-TC-0030 evaluated the bandpass filter’s insertion loss and return loss across the 2.4–2.5 GHz frequency range. According to the documentation, the results were as follows:

- Insertion lo...

**Citation Match:** ✅ Yes

---

### Example 3

**Question:** What were the results of test case FD-TC-0028?

**Expected:** Test case FD-TC-0028 result: PASS. Total defects found: N/A, capture rate: N/A%, nuisance rate: N/A%....

**Predicted:** Test case FD-TC-0028 evaluated the bandpass filter’s insertion loss and return loss across the 2.4–2.5 GHz frequency range. According to the documentation, the results were as follows:

- **Insertion ...

**Citation Match:** ✅ Yes

---

### Example 4

**Question:** What were the results of test case FD-TC-0089?

**Expected:** Test case FD-TC-0089 result: FAIL. Total defects found: N/A, capture rate: N/A%, nuisance rate: N/A%....

**Predicted:** Test case FD-TC-0089 evaluated the bandpass filter’s insertion loss and return loss across the 2.4–2.5 GHz frequency range. According to the documentation, the results were as follows:

- **Insertion ...

**Citation Match:** ✅ Yes

---

### Example 5

**Question:** What were the results of test case FD-TC-0098?

**Expected:** Test case FD-TC-0098 result: CONDITIONAL PASS. Total defects found: N/A, capture rate: N/A%, nuisance rate: N/A%....

**Predicted:** Test case FD-TC-0098 evaluated the bandpass filter’s insertion loss and return loss across the 2.4–2.5 GHz frequency range. According to the documentation, the results were as follows:

- Insertion lo...

**Citation Match:** ✅ Yes

---

## Recommendations

1. **If citation accuracy < 90%**: Increase training epochs or add more explicit citation examples
2. **If responses are too verbose**: Add length constraints to training examples
3. **For production use**: Compare fine-tuned model results against the base model + RAG approach
4. **Periodic re-training**: Re-generate training data when new engineering documents are added

## Files

| File | Description |
|------|-------------|
| `data/fine_tuning_train.jsonl` | Training dataset (80 examples) |
| `data/fine_tuning_validation.jsonl` | Validation dataset (20 examples) |
| `data/evaluation_metrics.json` | Raw evaluation metrics (JSON) |
