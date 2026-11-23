# Evaluation report

## Summary

| Metric | Value |
|---|---|
| questions | 17 |
| passed | 17 |
| answer_type_accuracy | 1.0 |
| path_accuracy | 1.0 |
| retrieval_hit_rate | 1.0 |
| citation_recall | 1.0 |
| citation_precision | 1.0 |
| latest_circular_correct | 1.0 |
| repeatable_across_runs | True |
| median_latency_ms | 2.07 |
| max_latency_ms | 4.06 |

## Per-question results

| ID | Tag | Graph path (final turn) | Answer type | Retrieved (top 4) | Cited | ms | Pass |
|---|---|---|---|---|---|---|---|
| Q01 | answer | interpret > retrieve > grade > answer | answer | ATT-2023-01#1, LAB-2023-06#2, EXM-2023-04#2, EXM-2024-08#1 | ATT-2023-01#1 | 2.22 | PASS |
| Q02 | policy_update | interpret > retrieve > grade > answer | answer_with_update | ATT-2024-03#1, ATT-2023-01#3, ATT-2024-03#2, ATT-2023-01#1 | ATT-2024-03#1 | 2.49 | PASS |
| Q03 | personal_record | interpret > retrieve > grade > answer | answer_with_update | ATT-2023-01#3, ATT-2024-03#1, ATT-2024-03#2, EXM-2024-08#1 | ATT-2024-03#1, ATT-2024-03#2 | 2.26 | PASS |
| Q04 | ambiguity | interpret > retrieve > grade > clarify | clarification | PRJ-2023-02#3, PRJ-2023-02#2, PRJ-2023-02#4, PRJ-2025-04#1 | - | 1.78 | PASS |
| Q05 | ambiguity+update | interpret > retrieve > grade > answer | answer_with_update | PRJ-2023-02#3, PRJ-2025-04#1, PRJ-2023-02#2, PRJ-2023-02#4 | PRJ-2025-04#1 | 4.05 | PASS |
| Q06 | answer | interpret > retrieve > grade > answer | answer | PRJ-2023-02#2, PRJ-2025-04#1, PRJ-2023-02#3, PRJ-2023-02#1 | PRJ-2023-02#2 | 2.17 | PASS |
| Q07 | ambiguity | interpret > retrieve > grade > clarify | clarification | LAB-2023-06#1, LAB-2023-06#2, LAB-2023-05#4, LAB-2023-06#3 | - | 2.02 | PASS |
| Q08 | ambiguity | interpret > retrieve > grade > answer | answer | LAB-2023-06#2, LAB-2023-06#3, ATT-2023-01#1, LAB-2023-06#1 | LAB-2023-06#2 | 4.06 | PASS |
| Q09 | guided_process | interpret > retrieve > grade > answer | answer_with_update | REV-2023-07#1, REV-2023-07#3, REV-2023-07#2, REV-2023-07#4 | REV-2023-07#1, REV-2023-07#3, REV-2025-02#1 | 1.96 | PASS |
| Q10 | policy_update | interpret > retrieve > grade > answer | answer_with_update | REV-2025-02#1, REV-2023-07#2, REV-2023-07#3, REV-2023-07#4 | REV-2025-02#1, REV-2023-07#3 | 2.05 | PASS |
| Q11 | out_of_scope | interpret > retrieve > grade > escalate | out_of_scope | - | - | 1.51 | PASS |
| Q12 | insufficient_evidence | interpret > retrieve > grade > escalate | insufficient_evidence | EXM-2023-04#4, EXM-2024-08#2, ATT-2023-01#4, LAB-2023-06#1 | - | 2.07 | PASS |
| Q13 | answer | interpret > retrieve > grade > answer | answer | LAB-2023-05#4, LAB-2023-05#3, LAB-2023-06#3, LAB-2023-06#4 | LAB-2023-05#4, LAB-2023-05#3 | 1.82 | PASS |
| Q14 | answer | interpret > retrieve > grade > answer | answer | EXM-2023-04#3, EXM-2023-04#2, EXM-2023-04#1, LAB-2023-05#4 | EXM-2023-04#3, EXM-2023-04#2 | 1.88 | PASS |
| Q15 | answer | interpret > retrieve > grade > answer | answer | EXM-2024-08#1, EXM-2024-08#2, LAB-2023-06#4, EXM-2023-04#2 | EXM-2024-08#1, EXM-2024-08#2 | 1.88 | PASS |
| Q16 | competing_references | interpret > retrieve > grade > answer | competing_references | PRJ-2023-02#3, PRJ-2023-02#2, PRJ-2023-02#4, PRJ-2025-04#1 | PRJ-2025-04#1, PRJ-2023-02#2 | 3.89 | PASS |
| Q17 | no_simulated_action | interpret > retrieve > grade > answer | answer | REV-2023-07#3, REV-2023-07#4, REV-2023-07#1, REV-2025-02#1 | REV-2023-07#3 | 2.56 | PASS |
