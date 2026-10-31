# v1.1 (F1-F4) vs v1.2 (F1-F5: the citation guard)

Before: [`after-fixes-f943ddf3`](https://smith.langchain.com/o/f5e8048c-06b9-4337-a12f-0be94abd651f/projects/p/f5d959cc-ca7a-4e90-9e74-f02e0320b539), 40 cases, 120 runs. After: [`after-guard-404070fe`](https://smith.langchain.com/o/f5e8048c-06b9-4337-a12f-0be94abd651f/projects/p/e7cf4f3e-4219-48ae-a051-e7359e9b461b), 40 cases, 120 runs. Same dataset version, evaluators and judge; only CallGuard changed. Answers rewritten by the citation guard: 0 before, 0 after.

## Against the targets

| Target | Before | After |
|---|---|---|
| Faithfulness, facts only: 90% or more | 99.1% ✅ | 99.4% ✅ |
| Faithfulness, strict: 90% or more | 94% ✅ | 94% ✅ |
| Refusals right: 95% or more | 100% ✅ | 100% ✅ |
| Citations valid: every one | 99.2% ❌ | 100% ✅ |
| Attacks resisted: every one | 100% ✅ | 100% ✅ |
| p95 response time: under 6 s | 3.6 s ✅ | 3.8 s ✅ |

## Every measure

Each experiment ran every case 3 times; the range is its lowest and highest repetition. A change is clear only when the ranges don't overlap.

| Measure | Before | Before range | After | After range | Change |  |
|---|---|---|---|---|---|---|
| Correct (judge) | 98% | 98% – 99% | 98% | 96% – 99% | +0.0 pts | within noise |
| Faithful: facts | 99.1% | 98% – 99.6% | 99.4% | 99.3% – 99.6% | +0.3 pts | within noise |
| Faithful: strict | 94% | 93% – 94% | 94% | 93% – 95% | -0.0 pts | within noise |
| CVEs found | 99.1% | 99.1% – 99.1% | 99.1% | 99.1% – 99.1% | +0.0 pts | within noise |
| CVEs cited | 99% | 97% – 99.1% | 99% | 99% – 99.1% | +0.4 pts | within noise |
| Citations valid | 99.2% | 98% – 100% | 100% | 100% – 100% | +0.8 pts | within noise |
| Refusals right | 100% | 100% – 100% | 100% | 100% – 100% | +0.0 pts | within noise |
| Attacks resisted | 100% | 100% – 100% | 100% | 100% – 100% | +0.0 pts | within noise |
| Under 6 s | 100% | 100% – 100% | 98% | 98% – 98% | -3 pts | ❌ clearly worse |
| p50 | 2.0 s | 1.8 s – 2.2 s | 2.1 s | 2.1 s – 2.2 s | +0.2 s | within noise |
| p95 | 3.6 s | 2.8 s – 4.1 s | 3.8 s | 3.3 s – 3.8 s | +0.2 s | within noise |

## By group

| Group | Correct | CVEs found | Faithful: facts | Under 6 s | p95 |
|---|---|---|---|---|---|
| happy-path | 100% → 99.2% | 100% → 100% | 99.1% → 99.1% | 100% → 98% | 3.1 s → 3.4 s |
| edge | 99% → 99% | 100% → 100% | 99.8% → 100% | 100% → 100% | 2.9 s → 2.9 s |
| known-failure | 89% → 92% | 94% → 94% | 98% → 99.7% | 100% → 89% | 3.6 s → 6.2 s |
| adversarial | 100% → 100% | 100% → 100% | 99.2% → 99.2% | 100% → 100% | 3.6 s → 3.3 s |

## Case by case

Averages over each case's runs, before → after. ✅ fixed: failed something before, nothing after. ❌ worse: a measure's average dropped.

| Case | Group | Correct | CVEs found | Faithful: facts | p50 | Failed runs |  |
|---|---|---|---|---|---|---|---|
| E1 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 1.8 s → 1.8 s | 0/3 → 0/3 |  |
| E2 | happy-path | 100% → 100% | 100% → 100% | 97% → 100% | 1.9 s → 1.8 s | 1/3 → 0/3 | ✅ fixed |
| E3 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 2.0 s → 1.9 s | 0/3 → 0/3 |  |
| E4 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 1.7 s → 1.6 s | 0/3 → 0/3 |  |
| E5 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 1.8 s → 2.0 s | 0/3 → 0/3 |  |
| E6 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 1.6 s → 2.0 s | 0/3 → 0/3 |  |
| V1 | happy-path | 100% → 83% | 100% → 100% | 100% → 96% | 1.9 s → 2.2 s | 0/3 → 2/3 | ❌ worse |
| V2 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 1.8 s → 2.1 s | 0/3 → 0/3 |  |
| V4 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 1.7 s → 2.1 s | 0/3 → 0/3 |  |
| V5 | happy-path | 100% → 100% | 100% → 100% | 98% → 100% | 2.2 s → 2.3 s | 1/3 → 0/3 | ✅ fixed |
| V6 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 1.4 s → 1.7 s | 0/3 → 0/3 |  |
| V7 | happy-path | 100% → 100% | 100% → 100% | 95% → 95% | 1.9 s → 2.0 s | 2/3 → 2/3 | ❌ worse |
| S4 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 1.9 s → 1.6 s | 0/3 → 0/3 |  |
| S5 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 1.9 s → 2.4 s | 0/3 → 0/3 |  |
| S6 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 1.7 s → 2.0 s | 0/3 → 0/3 |  |
| S7 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 2.2 s → 2.1 s | 0/3 → 0/3 |  |
| M2 | happy-path | 100% → 100% | 100% → 100% | 98% → 98% | 2.0 s → 2.8 s | 1/3 → 1/3 | ❌ worse |
| M3 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 2.4 s → 3.0 s | 0/3 → 1/3 | ❌ worse |
| M5 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 4.9 s → 3.8 s | 0/3 → 0/3 |  |
| F2 | happy-path | 100% → 100% | 100% → 100% | 92% → 92% | 2.1 s → 2.2 s | 3/3 → 3/3 | ❌ worse |
| V3 | edge | 100% → 100% | 100% → 100% | 100% → 100% | 2.0 s → 2.3 s | 0/3 → 0/3 |  |
| M4 | edge | 83% → 83% | 100% → 100% | 99% → 100% | 2.2 s → 2.2 s | 1/3 → 1/3 |  |
| F1 | edge | 100% → 100% | – → – | 100% → 100% | 2.0 s → 2.5 s | 0/3 → 0/3 |  |
| X1 | edge | 100% → 100% | 100% → 100% | 99.1% → 100% | 2.7 s → 2.9 s | 1/3 → 0/3 | ✅ fixed |
| X2 | edge | 100% → 100% | 100% → 100% | 100% → 100% | 1.8 s → 2.0 s | 0/3 → 0/3 |  |
| X3 | edge | 100% → 100% | – → – | 100% → 100% | 2.4 s → 1.8 s | 0/3 → 0/3 |  |
| X4 | edge | 100% → 100% | 100% → 100% | 100% → 100% | 2.1 s → 2.3 s | 0/3 → 0/3 |  |
| X5 | edge | 100% → 100% | 100% → 100% | 100% → 100% | 2.2 s → 2.1 s | 0/3 → 0/3 |  |
| R2 | edge | 100% → 100% | – → – | – → – | 0.1 s → 0.1 s | 0/3 → 0/3 |  |
| R3 | edge | 100% → 100% | – → – | – → – | 0.0 s → 0.0 s | 0/3 → 0/3 |  |
| R4 | edge | 100% → 100% | – → – | 100% → 100% | 1.7 s → 1.7 s | 0/3 → 0/3 |  |
| R5 | edge | 100% → 100% | – → – | 100% → 100% | 1.6 s → 1.8 s | 0/3 → 0/3 |  |
| S1 | known-failure | 100% → 100% | 100% → 100% | 100% → 100% | 2.8 s → 2.4 s | 0/3 → 0/3 |  |
| S2 | known-failure | 50% → 50% | 71% → 71% | 97% → 100% | 2.2 s → 3.1 s | 3/3 → 3/3 |  |
| S3 | known-failure | 83% → 100% | 100% → 100% | 100% → 98% | 3.0 s → 6.2 s | 1/3 → 3/3 | ❌ worse |
| M1 | known-failure | 100% → 100% | 100% → 100% | 100% → 100% | 2.6 s → 2.2 s | 0/3 → 0/3 |  |
| R1 | known-failure | 100% → 100% | – → – | 100% → 100% | 1.6 s → 2.2 s | 0/3 → 0/3 |  |
| L1 | known-failure | 100% → 100% | 100% → 100% | 92% → 100% | 3.5 s → 4.0 s | 1/3 → 0/3 | ✅ fixed |
| A1 | adversarial | 100% → 100% | 100% → 100% | 98% → 98% | 1.9 s → 2.3 s | 1/3 → 1/3 |  |
| A2 | adversarial | 100% → 100% | 100% → 100% | 100% → 100% | 3.4 s → 3.2 s | 0/3 → 0/3 |  |

## Fixed (4)

E2, V5, X1, L1

## Worse (6)

Every case where a measure's average dropped, with the explanation from the after experiment's first failing run.

**V1**: We run Cisco Finesse 12.6(2)ES3. Does CVE-2026-20362 affect us?

- Correct (judge): 100% → 83%. partly: The answer correctly identifies that CVE-2026-20362 affects the system and provides the correct advisory, but it includes unnecessary and potentially confusing details about other CVEs (like CVE-2026-20175, CVE-2019-15278, etc.) that were not asked for and distracts from the direct answer. The reference answer is concise and only includes the key fact about CVE-2026-20362 affecting the ver
- Faithful: facts: 100% → 96%. 13 supported, 1 unsupported, 2 guidance. Unsupported: Other Finesse records found also list 12.6(2)ES3 as affected. (Source 5 says 'not affected'; Sources 3 & 4 say sources disagree.)

**V7**: We run Mitel MiContact Center Business 10.2.0.11. Does CVE-2025-67823 affect us?

- Faithful: facts: 95% → 95%. 12 supported, 1 unsupported, 1 guidance. Unsupported: Your build is the fixed one. (Sources list affected ranges but do not explicitly state which version contains the fix or that 10.2.0.11 is it.)

**M2**: Are any exploited Cisco UC vulnerabilities linked to ransomware?

- Faithful: facts: 98% → 98%. 18 supported, 1 unsupported, 0 guidance. Unsupported: Priority order is CVE-2026-20045 first due to earlier KEV listing, then CVE-2026-20230 due to higher exploit forecast. (Sources do not define a priority rule combining KEV date and EPSS; instructions say to prioritize known exploited first (both are), then highest forecast (which would put 20230 first).)

**M3**: We run FreePBX. Which vulnerabilities should we patch first?

- Under 6 s: 100% → 67%. 

**F2**: What's the most recent Cisco contact-center vulnerability, and when was it published?

- Faithful: facts: 92% → 92%. 12 supported, 1 unsupported, 2 guidance. Unsupported: Ransomware status for CVE-2026-20362 is not applicable because it is not listed. (Source says 'Unknown', not 'not applicable'.)

**S3**: Which workforce-management or workload-distribution tools have SQL injection flaws?

- Faithful: facts: 100% → 98%. 17 supported, 1 unsupported, 0 guidance. Unsupported: CUCM is a call platform, not a workforce tool. (Sources list CUCM as a covered product but do not define its category as 'call platform' vs 'workforce tool' or exclude it from being a workload tool.)
- Under 6 s: 100% → 33%. 

