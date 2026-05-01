# Ranking & Feedback Loop — Evaluation Report

## Summary

| Metric | Value |
|--------|-------|
| **Total Queries Evaluated** | 10 |
| **Search Ranking Accuracy** | 70.0% |
| **Agent Citation Accuracy** | 90.0% |
| **Feedback Entries Collected** | 27 |
| **Evaluation Date** | 2026-05-01 |

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
| 1 | What are the key design specifications in the latest enginee | Yes | filter_design_active_rc_lp_05.pptx | 1.8786 | No |
| 2 | Which presentations cover system architecture decisions? | No | N/A | 0 | Yes |
| 3 | What trade-off analyses were performed for material selectio | Yes | filter_design_butterworth_lp_01.pptx | 1.1046 | Yes |
| 4 | How are thermal constraints addressed in the design? | Yes | filter_design_active_rc_lp_01.pptx | 1.5931 | Yes |
| 5 | What project milestones are documented in the presentations? | Yes | filter_design_chebyshev2_lp_05.pptx | 1.5704 | Yes |
| 6 | Which design reviews identified critical risks? | Yes | filter_design_chebyshev2_lp_05.pptx | 1.2911 | Yes |
| 7 | What manufacturing process changes were proposed? | No | N/A | 0 | Yes |
| 8 | How do tolerance requirements affect design decisions? | Yes | filter_design_active_rc_lp_05.pptx | 1.3733 | Yes |
| 9 | What testing methodologies are described in the presentation | No | N/A | 0 | Yes |
| 10 | What reliability testing results are documented? | Yes | filter_design_butterworth_lp_10.pptx | 1.6165 | Yes |

## Recommendations

1. **Collect More Feedback**: Run the agent in production with feedback collection enabled to accumulate data for re-ranking.
2. **Periodic Re-Indexing**: Re-run `chunk_and_index.py` after document updates to keep the chunked index fresh.
3. **A/B Test Scoring Weights**: Experiment with different scoring profile weights to find the optimal configuration.
4. **Fine-Tune on Feedback Data**: Use positive feedback pairs as additional fine-tuning examples to improve the model's domain knowledge.
5. **Monitor Drift**: Track accuracy weekly; re-train if citation accuracy drops below 93%.
