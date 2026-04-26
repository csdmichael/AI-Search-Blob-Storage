# Fine-Tuning Evaluation Results

## Summary

| Metric | Value |
|--------|-------|
| **Base Model** | `gpt-4.1` |
| **Fine-Tuned Model** | `gpt-4.1` |
| **Evaluation Date** | 2026-04-26 |
| **Training Examples** | 539 |
| **Validation Examples** | 135 |
| **Evaluated Samples** | 50 |
| **Citation Accuracy** | 90.0% |
| **Avg Tokens/Query** | 222.8 |

## Methodology

### Training Data Generation
- Q&A pairs were automatically extracted from all 100 KLA engineering test case documents
- Each document yields 5-7 question-answer pairs covering: objectives, results, systems, acceptance criteria, observations, and corrective actions
- Training/validation split: 80/20 with fixed random seed for reproducibility

### Fine-Tuning Configuration
- Base model: `gpt-4.1`
- Epochs: 3
- Batch size: auto
- Learning rate multiplier: auto
- Suffix: `kla-eng-docs`

### Evaluation Criteria
1. **Citation Accuracy**: Does the response correctly cite the relevant KLA-MFG-TC document number?
2. **Response Relevance**: Does the response contain key information from the expected answer?
3. **Token Efficiency**: Average tokens used per query (lower is better for cost)

## Detailed Results

| # | Question | Citation Match | Prompt Tokens | Completion Tokens |
|---|----------|:--------------:|:-------------:|:-----------------:|
| 1 | What does test case KLA-MFG-TC-0028 cover? | ✅ | 76 | 86 |
| 2 | What does test case KLA-MFG-TC-0077 cover? | ✅ | 76 | 98 |
| 3 | What test cases involve the Archer 750 system? | ❌ | 71 | 179 |
| 4 | What are the acceptance criteria for KLA-MFG-TC-0001? | ✅ | 77 | 217 |
| 5 | What are the acceptance criteria for KLA-MFG-TC-0091? | ✅ | 77 | 222 |
| 6 | What test cases involve the Candela 8520 system? | ❌ | 73 | 241 |
| 7 | What were the results of test case KLA-MFG-TC-0067? | ✅ | 78 | 147 |
| 8 | Which inspection system is used in KLA-MFG-TC-0093 and what defects does it targ | ✅ | 83 | 51 |
| 9 | What corrective actions are recommended in KLA-MFG-TC-0100? | ✅ | 77 | 211 |
| 10 | Which inspection system is used in KLA-MFG-TC-0096 and what defects does it targ | ✅ | 83 | 54 |
| 11 | What were the results of test case KLA-MFG-TC-0097? | ✅ | 78 | 163 |
| 12 | What does test case KLA-MFG-TC-0094 cover? | ✅ | 76 | 113 |
| 13 | What were the results of test case KLA-MFG-TC-0018? | ✅ | 78 | 158 |
| 14 | What observations were noted in KLA-MFG-TC-0002? | ✅ | 76 | 124 |
| 15 | What does test case KLA-MFG-TC-0039 cover? | ✅ | 76 | 117 |
| 16 | Which inspection system is used in KLA-MFG-TC-0081 and what defects does it targ | ✅ | 83 | 54 |
| 17 | What were the results of test case KLA-MFG-TC-0072? | ✅ | 78 | 200 |
| 18 | What were the results of test case KLA-MFG-TC-0059? | ✅ | 78 | 151 |
| 19 | What corrective actions are recommended in KLA-MFG-TC-0059? | ✅ | 77 | 166 |
| 20 | What corrective actions are recommended in KLA-MFG-TC-0010? | ✅ | 77 | 198 |
| 21 | What are the acceptance criteria for KLA-MFG-TC-0096? | ✅ | 77 | 218 |
| 22 | What observations were noted in KLA-MFG-TC-0096? | ✅ | 76 | 130 |
| 23 | What does test case KLA-MFG-TC-0024 cover? | ✅ | 76 | 109 |
| 24 | What are the acceptance criteria for KLA-MFG-TC-0017? | ✅ | 77 | 218 |
| 25 | What does test case KLA-MFG-TC-0008 cover? | ✅ | 76 | 103 |
| 26 | What corrective actions are recommended in KLA-MFG-TC-0014? | ✅ | 77 | 191 |
| 27 | What does test case KLA-MFG-TC-0076 cover? | ✅ | 76 | 96 |
| 28 | Which inspection system is used in KLA-MFG-TC-0078 and what defects does it targ | ✅ | 83 | 54 |
| 29 | What corrective actions are recommended in KLA-MFG-TC-0021? | ✅ | 77 | 193 |
| 30 | What were the results of test case KLA-MFG-TC-0089? | ✅ | 78 | 156 |
| 31 | What were the results of test case KLA-MFG-TC-0093? | ✅ | 78 | 164 |
| 32 | What corrective actions are recommended in KLA-MFG-TC-0061? | ✅ | 77 | 168 |
| 33 | What were the results of test case KLA-MFG-TC-0066? | ✅ | 78 | 138 |
| 34 | What test cases involve the Surfscan SP5 system? | ❌ | 72 | 199 |
| 35 | What corrective actions are recommended in KLA-MFG-TC-0082? | ✅ | 77 | 177 |
| 36 | What were the results of test case KLA-MFG-TC-0038? | ✅ | 78 | 148 |
| 37 | What does test case KLA-MFG-TC-0100 cover? | ✅ | 76 | 101 |
| 38 | What were the results of test case KLA-MFG-TC-0041? | ✅ | 78 | 191 |
| 39 | What are the acceptance criteria for KLA-MFG-TC-0022? | ✅ | 77 | 236 |
| 40 | What observations were noted in KLA-MFG-TC-0070? | ✅ | 76 | 114 |
| 41 | Which inspection system is used in KLA-MFG-TC-0061 and what defects does it targ | ✅ | 83 | 51 |
| 42 | What test cases involve the Candela 8520 system? | ❌ | 73 | 180 |
| 43 | What were the results of test case KLA-MFG-TC-0033? | ✅ | 78 | 191 |
| 44 | What test cases involve the Puma 9900 system? | ❌ | 72 | 192 |
| 45 | What does test case KLA-MFG-TC-0087 cover? | ✅ | 76 | 99 |
| 46 | What does test case KLA-MFG-TC-0033 cover? | ✅ | 76 | 93 |
| 47 | What does test case KLA-MFG-TC-0011 cover? | ✅ | 76 | 93 |
| 48 | What observations were noted in KLA-MFG-TC-0041? | ✅ | 76 | 129 |
| 49 | What does test case KLA-MFG-TC-0062 cover? | ✅ | 76 | 109 |
| 50 | What does test case KLA-MFG-TC-0049 cover? | ✅ | 76 | 99 |

## Sample Predictions

### Example 1

**Question:** What does test case KLA-MFG-TC-0028 cover?

**Expected:** Test case KLA-MFG-TC-0028 covers: CD-SEM Measurement - Edge Placement Error Detection on 5D Analyzer. This test case validates the capability of the 5D Analyzer system to detect
and classify Edge Plac...

**Predicted:** Test case **KLA-MFG-TC-0028** covers the **verification of the system’s ability to detect sub-micron particle defects on 300mm silicon wafers during the standard inspection cycle**. This includes vali...

**Citation Match:** ✅ Yes

---

### Example 2

**Question:** What does test case KLA-MFG-TC-0077 cover?

**Expected:** Test case KLA-MFG-TC-0077 covers: Wafer Geometry Measurement - Corrosion Detection on Surfscan SP5. This test case validates the capability of the Surfscan SP5 system to detect
and classify Corrosion ...

**Predicted:** Test case **KLA-MFG-TC-0077** covers the **detection and classification of sub-micron particle defects on 300mm silicon wafers using the SP7xx series inspection tool**. It verifies the tool’s ability ...

**Citation Match:** ✅ Yes

---

### Example 3

**Question:** What test cases involve the Archer 750 system?

**Expected:** Test case KLA-MFG-TC-0085 involves the Archer 750 system for Extra Pattern detection at the 3nm node (Pre-Diffusion). Refer to the full index for other test cases using this system....

**Predicted:** The Archer 750 system is referenced in several test cases related to overlay metrology and defect detection. According to the engineering documentation:

- **KLA-MFG-TC-1123**: "Archer 750 Overlay Acc...

**Citation Match:** ❌ No

---

### Example 4

**Question:** What are the acceptance criteria for KLA-MFG-TC-0001?

**Expected:** Acceptance criteria for KLA-MFG-TC-0001:
- Defect detection sensitivity must meet 45nm node requirements
- False positive rate shall not exceed 5% of total detected events
- Scan throughput must be ≥ ...

**Predicted:** According to engineering documentation KLA-MFG-TC-0001, the acceptance criteria are as follows:

1. **Defect Detection Sensitivity:**  
   The inspection system must detect all programmed defects ≥ 0....

**Citation Match:** ✅ Yes

---

### Example 5

**Question:** What are the acceptance criteria for KLA-MFG-TC-0091?

**Expected:** Acceptance criteria for KLA-MFG-TC-0091:
- Defect detection sensitivity must meet 14nm node requirements
- False positive rate shall not exceed 5% of total detected events
- Scan throughput must be ≥ ...

**Predicted:** According to engineering documentation KLA-MFG-TC-0091, the acceptance criteria are as follows:

1. **Defect Detection Sensitivity:**  
   The inspection system must detect all programmed test defects...

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
| `data/fine_tuning_train.jsonl` | Training dataset (539 examples) |
| `data/fine_tuning_validation.jsonl` | Validation dataset (135 examples) |
| `data/evaluation_metrics.json` | Raw evaluation metrics (JSON) |
