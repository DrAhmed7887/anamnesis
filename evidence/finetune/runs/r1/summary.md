| System | Split | n | Valid JSON | Dropped by checks | Invalid JSON | No reply | Fully right | Missing / extra | Harmful before / after |
|---|---|---|---|---|---|---|---|---|---|
| Spark 1.3 | test_iid | 100 | 100 | 0 | 0 | 0 | 63 | 0 / 0 | 1 / 1 |
| Spark 1.3 | test_shift | 120 | 120 | 0 | 0 | 0 | 79 | 0 / 0 | 0 / 0 |
| Spark 1.3 | test_codeswitch | 50 | 50 | 0 | 0 | 0 | 31 | 0 / 0 | 0 / 0 |
| Spark 1.3 | test_real | 33 | 33 | 0 | 0 | 0 | 20 | 0 / 1 | 0 / 0 |
| **Spark 1.3** | **all** | **303** | **303** | **0** | **0** | **0** | **193** | **0 / 1** | **1 / 1** |
| Glimmer base | test_iid | 100 | 87 | 4 | 13 | 0 | 20 | 39 / 1 | 40 / 22 |
| Glimmer base | test_shift | 120 | 107 | 13 | 13 | 0 | 17 | 56 / 0 | 42 / 19 |
| Glimmer base | test_codeswitch | 50 | 41 | 4 | 9 | 0 | 6 | 28 / 0 | 11 / 6 |
| Glimmer base | test_real | 33 | 32 | 2 | 1 | 0 | 7 | 8 / 1 | 11 / 7 |
| **Glimmer base** | **all** | **303** | **267** | **23** | **36** | **0** | **50** | **131 / 2** | **104 / 54** |
| Glimmer + LoRA | test_iid | 100 | 100 | 0 | 0 | 0 | 100 | 0 / 0 | 0 / 0 |
| Glimmer + LoRA | test_shift | 120 | 120 | 0 | 0 | 0 | 113 | 0 / 0 | 0 / 0 |
| Glimmer + LoRA | test_codeswitch | 50 | 50 | 0 | 0 | 0 | 47 | 0 / 0 | 0 / 0 |
| Glimmer + LoRA | test_real | 33 | 33 | 0 | 0 | 0 | 30 | 0 / 0 | 0 / 0 |
| **Glimmer + LoRA** | **all** | **303** | **303** | **0** | **0** | **0** | **290** | **0 / 0** | **0 / 0** |

| System | name_text | inn | intake | strength | units_per_intake | intakes_per_day | as_needed | status |
|---|---|---|---|---|---|---|---|---|
| Spark 1.3 | 519/547 | 547/547 | 506/547 | 538/547 | 547/547 | 530/547 | 522/547 | 520/547 |
| Glimmer base | 396/547 | 320/547 | 294/547 | 384/547 | 384/547 | 362/547 | 276/547 | 382/547 |
| Glimmer + LoRA | 542/547 | 547/547 | 541/547 | 545/547 | 547/547 | 547/547 | 546/547 | 546/547 |

Glimmer base: never opened an answer 0, answer stopped at the token limit 36
Glimmer + LoRA: never opened an answer 0, answer stopped at the token limit 0
