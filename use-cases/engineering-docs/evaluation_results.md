# Fine-Tuning Evaluation Results

## Summary

| Metric | Value |
|--------|-------|
| **Base Model** | `gpt-4.1` |
| **Fine-Tuned Model** | `gpt-4.1` |
| **Evaluation Date** | 2026-04-27 |
| **Training Examples** | 540 |
| **Validation Examples** | 135 |
| **Evaluated Samples** | 50 |
| **Citation Accuracy** | 74.0% |
| **Avg Tokens/Query** | 205.1 |

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
- Suffix: `eng-docs`

### Evaluation Criteria
1. **Citation Accuracy**: Does the response correctly cite the relevant MFG-TC document number?
2. **Response Relevance**: Does the response contain key information from the expected answer?
3. **Token Efficiency**: Average tokens used per query (lower is better for cost)

## Detailed Results

| # | Question | Citation Match | Prompt Tokens | Completion Tokens |
|---|----------|:--------------:|:-------------:|:-----------------:|
| 1 | What test cases involve the Zeta-388 system? | ❌ | 68 | 173 |
| 2 | What corrective actions are recommended in MFG-TC-0085? | ✅ | 71 | 145 |
| 3 | What are the acceptance criteria for MFG-TC-0001? | ✅ | 71 | 147 |
| 4 | Which inspection system is used in MFG-TC-0091 and what defects does it target? | ✅ | 77 | 48 |
| 5 | What test cases involve the Puma 9xxx system? | ❌ | 68 | 178 |
| 6 | What test cases involve the Zeta-388 system? | ❌ | 68 | 131 |
| 7 | What were the results of test case MFG-TC-0093? | ✅ | 72 | 183 |
| 8 | What corrective actions are recommended in MFG-TC-0100? | ✅ | 71 | 201 |
| 9 | What were the results of test case MFG-TC-0096? | ✅ | 72 | 180 |
| 10 | Which inspection system is used in MFG-TC-0099 and what defects does it target? | ✅ | 77 | 58 |
| 11 | What does test case MFG-TC-0094 cover? | ✅ | 70 | 79 |
| 12 | What are the acceptance criteria for MFG-TC-0018? | ✅ | 71 | 152 |
| 13 | What observations were noted in MFG-TC-0002? | ✅ | 70 | 109 |
| 14 | What were the results of test case MFG-TC-0039? | ✅ | 72 | 190 |
| 15 | What were the results of test case MFG-TC-0081? | ✅ | 72 | 182 |
| 16 | What does test case MFG-TC-0072 cover? | ✅ | 70 | 86 |
| 17 | What test cases involve the Surfscan SP7 system? | ❌ | 68 | 178 |
| 18 | What are the acceptance criteria for MFG-TC-0059? | ✅ | 71 | 184 |
| 19 | What observations were noted in MFG-TC-0010? | ✅ | 70 | 108 |
| 20 | Which inspection system is used in MFG-TC-0096 and what defects does it target? | ✅ | 77 | 48 |
| 21 | What are the acceptance criteria for MFG-TC-0096? | ✅ | 71 | 157 |
| 22 | What does test case MFG-TC-0024 cover? | ✅ | 70 | 98 |
| 23 | What observations were noted in MFG-TC-0017? | ✅ | 70 | 108 |
| 24 | What were the results of test case MFG-TC-0008? | ✅ | 72 | 184 |
| 25 | What corrective actions are recommended in MFG-TC-0014? | ✅ | 71 | 188 |
| 26 | What test cases involve the Teron 640 system? | ❌ | 68 | 130 |
| 27 | What were the results of test case MFG-TC-0078? | ✅ | 72 | 148 |
| 28 | What test cases involve the 2920 Series system? | ❌ | 68 | 166 |
| 29 | What test cases involve the Teron SL650 system? | ❌ | 68 | 125 |
| 30 | What does test case MFG-TC-0093 cover? | ✅ | 70 | 96 |
| 31 | What are the acceptance criteria for MFG-TC-0061? | ✅ | 71 | 156 |
| 32 | What test cases involve the Teron SL650 system? | ❌ | 68 | 125 |
| 33 | What were the results of test case MFG-TC-0041? | ✅ | 72 | 118 |
| 34 | What observations were noted in MFG-TC-0082? | ✅ | 70 | 96 |
| 35 | What test cases involve the Archer 700 system? | ❌ | 67 | 165 |
| 36 | What are the acceptance criteria for MFG-TC-0038? | ✅ | 71 | 157 |
| 37 | What does test case MFG-TC-0100 cover? | ✅ | 70 | 77 |
| 38 | What are the acceptance criteria for MFG-TC-0041? | ✅ | 71 | 178 |
| 39 | What observations were noted in MFG-TC-0022? | ✅ | 70 | 126 |
| 40 | What are the acceptance criteria for MFG-TC-0070? | ✅ | 71 | 177 |
| 41 | What does test case MFG-TC-0061 cover? | ✅ | 70 | 93 |
| 42 | What corrective actions are recommended in MFG-TC-0076? | ✅ | 71 | 136 |
| 43 | What are the acceptance criteria for MFG-TC-0033? | ✅ | 71 | 155 |
| 44 | What test cases involve the Archer 700 system? | ❌ | 67 | 163 |
| 45 | What test cases involve the Archer 750 system? | ❌ | 67 | 128 |
| 46 | Which inspection system is used in MFG-TC-0033 and what defects does it target? | ✅ | 77 | 51 |
| 47 | What test cases involve the Teron SL650 system? | ❌ | 68 | 125 |
| 48 | What test cases involve the Teron SL650 system? | ❌ | 68 | 125 |
| 49 | What corrective actions are recommended in MFG-TC-0061? | ✅ | 71 | 133 |
| 50 | What does test case MFG-TC-0049 cover? | ✅ | 70 | 86 |

## Sample Predictions

### Example 1

**Question:** What test cases involve the Zeta-388 system?

**Expected:** Test case MFG-TC-0076 involves the Zeta-388 system for Contamination detection at the 45nm node (Final Inspection). Refer to the full index for other test cases using this system....

**Predicted:** The Zeta-388 system is referenced in the following test cases:

- **MFG-TC-1023:** "Zeta-388 Automated Surface Defect Inspection" – This test case details the use of the Zeta-388 system for detecting ...

**Citation Match:** ❌ No

---

### Example 2

**Question:** What corrective actions are recommended in MFG-TC-0085?

**Expected:** Corrective actions for MFG-TC-0085:
The following corrective actions are recommended:

1. Review edge-zone detection parameters for optimization.
2. Schedule follow-up test after recipe optimization.
...

**Predicted:** According to MFG-TC-0085, the recommended corrective actions include:

1. **Immediate Equipment Calibration:** Recalibrate the inspection equipment to ensure measurement accuracy.
2. **Process Paramet...

**Citation Match:** ✅ Yes

---

### Example 3

**Question:** What are the acceptance criteria for MFG-TC-0001?

**Expected:** Acceptance criteria for MFG-TC-0001:
- Defect detection sensitivity must meet 22nm node requirements
- False positive rate shall not exceed 5% of total detected events
- Scan throughput must be ≥ 120 ...

**Predicted:** The acceptance criteria for MFG-TC-0001 are as follows:

1. No critical defects (Class 1) are permitted on any inspected semiconductor wafer.
2. The total number of major defects (Class 2) must not ex...

**Citation Match:** ✅ Yes

---

### Example 4

**Question:** Which inspection system is used in MFG-TC-0091 and what defects does it target?

**Expected:** Test case MFG-TC-0091 uses the Teron 640 system to detect Micro-cracks defects during the Post-Deposition step at the 28nm technology node, located at Dresden Fab 3....

**Predicted:** According to document MFG-TC-0091, the inspection system used is the KLA-Tencor 2365 optical inspection system. This system targets surface particle contamination, pattern misalignment, and photoresis...

**Citation Match:** ✅ Yes

---

### Example 5

**Question:** What test cases involve the Puma 9xxx system?

**Expected:** Test case MFG-TC-0024 involves the Puma 9xxx system for Pits detection at the 28nm node (Post-Planarization). Refer to the full index for other test cases using this system....

**Predicted:** The Puma 9xxx system is referenced in the following test cases:

- **MFG-TC-1023:** "Puma 9xxx Automated Optical Inspection (AOI) – Baseline Defect Detection"  
  *Covers initial setup and validation ...

**Citation Match:** ❌ No

---

## Recommendations

1. **If citation accuracy < 90%**: Increase training epochs or add more explicit citation examples
2. **If responses are too verbose**: Add length constraints to training examples
3. **For production use**: Compare fine-tuned model results against the base model + RAG approach
4. **Periodic re-training**: Re-generate training data when new engineering documents are added

## Files

| File | Description |
|------|-------------|
| `data/fine_tuning_train.jsonl` | Training dataset (540 examples) |
| `data/fine_tuning_validation.jsonl` | Validation dataset (135 examples) |
| `data/evaluation_metrics.json` | Raw evaluation metrics (JSON) |
