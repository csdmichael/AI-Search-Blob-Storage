# Ranking & Feedback Loop — Evaluation Report

## Summary

| Metric | Value |
|--------|-------|
| **Total Queries Evaluated** | 10 |
| **Search Ranking Accuracy** | 100.0% |
| **Agent Citation Accuracy** | 70.0% |
| **Feedback Entries Collected** | 90 |
| **Evaluation Date** | 2026-04-27 |

## Approach — From 90% to 95%

The following techniques are applied to improve accuracy beyond the baseline 90%:

1. **Feedback-Driven Re-Ranking**: User feedback (relevant/irrelevant) is collected per query-document pair. Documents with consistently positive feedback receive a boost factor (up to 1.5×) applied on top of the semantic reranker score.

2. **Relevance Threshold Filtering**: Results below a configurable relevance threshold (0.7) are suppressed, reducing noise in agent context.

3. **Section-Level Chunking**: The chunked index provides more granular matches, so the agent gets precisely the relevant section instead of the full document.

4. **Custom Scoring Profile**: Title (3×), document number (2.5×), and section name (2×) are boosted relative to generic content (1×).

5. **Strict Agent Instructions**: The agent is instructed to never fabricate information, always cite sources, and respond with "not found" when the index has no relevant results.

## Detailed Results

| # | Query | Search Hit | Top Doc | Score | Agent Cited |
|---|-------|:----------:|---------|------:|:-----------:|
| 1 | What filter designs target 5G NR sub-6 GHz bands? | Yes | FD-TC-0096.pdf | 3.2151 | Yes |
| 2 | Which BAW filters have insertion loss below 1.5 dB? | Yes | FD-TC-0077.pdf | 2.5941 | No |
| 3 | Show test cases for TC-SAW temperature stability. | Yes | FD-TC-0071.pdf | 2.8012 | Yes |
| 4 | What are the acceptance criteria for duplexer isolation? | Yes | FD-TC-0042.pdf | 2.9344 | Yes |
| 5 | Which filter designs failed and what corrective actions exis | Yes | FD-TC-0068.pdf | 3.0585 | Yes |
| 6 | What substrate materials are used for FBAR filters? | Yes | FD-TC-0078.pdf | 3.1392 | No |
| 7 | Find WiFi 6E coexistence filter test results. | Yes | FD-TC-0070.pdf | 3.0017 | No |
| 8 | What is the Q factor for Band 7 SAW filters? | Yes | FD-TC-0019.pdf | 2.4326 | Yes |
| 9 | List corrective actions for high insertion loss designs. | Yes | FD-TC-0058.pdf | 2.486 | Yes |
| 10 | What design tools are used for 5G NR filter simulation? | Yes | FD-TC-0068.pdf | 3.5051 | Yes |

## Recommendations

1. **Collect More Feedback**: Run the agent in production with feedback collection enabled to accumulate data for re-ranking.
2. **Periodic Re-Indexing**: Re-run `chunk_and_index.py` after document updates to keep the chunked index fresh.
3. **A/B Test Scoring Weights**: Experiment with different scoring profile weights to find the optimal configuration.
4. **Fine-Tune on Feedback Data**: Use positive feedback pairs as additional fine-tuning examples to improve the model's domain knowledge.
5. **Monitor Drift**: Track accuracy weekly; re-train if citation accuracy drops below 93%.
