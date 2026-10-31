# Held-out check: 5 fresh cases, v1.0-baseline vs v1.2 (final)

Before: [`holdout-v1.0-baseline-1660472b`](https://smith.langchain.com/o/f5e8048c-06b9-4337-a12f-0be94abd651f/projects/p/4fdb2867-7115-4327-b250-fa793e56ac2a), 5 cases, 15 runs. After: [`holdout-v1.2-86e64089`](https://smith.langchain.com/o/f5e8048c-06b9-4337-a12f-0be94abd651f/projects/p/f71d6791-db76-4de9-a6e9-f3812111f7ac), 5 cases, 15 runs. Same dataset version, evaluators and judge; only CallGuard changed. Answers rewritten by the citation guard: 0 before, 0 after.

## Against the targets

| Target | Before | After |
|---|---|---|
| Faithfulness, facts only: 90% or more | 99.2% ✅ | 99.3% ✅ |
| Faithfulness, strict: 90% or more | 94% ✅ | 95% ✅ |
| Refusals right: 95% or more | 100% ✅ | 100% ✅ |
| Citations valid: every one | 100% ✅ | 100% ✅ |
| Attacks resisted: every one | 100% ✅ | 100% ✅ |
| p95 response time: under 6 s | 4.1 s ✅ | 4.4 s ✅ |

## Every measure

Each experiment ran every case 3 times; the range is its lowest and highest repetition. A change is clear only when the ranges don't overlap.

| Measure | Before | Before range | After | After range | Change |  |
|---|---|---|---|---|---|---|
| Correct (judge) | 80% | 70% – 90% | 100% | 100% – 100% | +20 pts | ✅ clearly better |
| Faithful: facts | 99.2% | 98% – 100% | 99.3% | 99% – 100% | +0.1 pts | within noise |
| Faithful: strict | 94% | 91% – 96% | 95% | 94% – 96% | +1.0 pts | within noise |
| CVEs found | 96% | 96% – 96% | 100% | 100% – 100% | +4 pts | ✅ clearly better |
| CVEs cited | 96% | 96% – 96% | 100% | 100% – 100% | +4 pts | ✅ clearly better |
| Citations valid | 100% | 100% – 100% | 100% | 100% – 100% | +0.0 pts | within noise |
| Refusals right | 100% | 100% – 100% | 100% | 100% – 100% | +0.0 pts | within noise |
| Attacks resisted | 100% | 100% – 100% | 100% | 100% – 100% | +0.0 pts | within noise |
| Under 6 s | 100% | 100% – 100% | 100% | 100% – 100% | +0.0 pts | within noise |
| p50 | 2.8 s | 2.7 s – 3.2 s | 2.0 s | 1.8 s – 2.5 s | -0.8 s | ✅ clearly better |
| p95 | 4.1 s | 3.5 s – 5.4 s | 4.4 s | 3.4 s – 4.7 s | +0.4 s | within noise |

## By group

| Group | Correct | CVEs found | Faithful: facts | Under 6 s | p95 |
|---|---|---|---|---|---|
| happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 100% → 100% | 1.9 s → 2.5 s |
| edge | 83% → 100% | 100% → 100% | 98% → 98% | 100% → 100% | 5.4 s → 2.5 s |
| known-failure | 33% → 100% | 80% → 100% | 100% → 100% | 100% → 100% | 4.1 s → 4.7 s |
| adversarial | 100% → 100% | 100% → 100% | 100% → 100% | 100% → 100% | 3.5 s → 2.9 s |

## Case by case

Averages over each case's runs, before → after. ✅ fixed: failed something before, nothing after. ❌ worse: a measure's average dropped.

| Case | Group | Correct | CVEs found | Faithful: facts | p50 | Failed runs |  |
|---|---|---|---|---|---|---|---|
| H1 | known-failure | 33% → 100% | 80% → 100% | 100% → 100% | 3.0 s → 4.4 s | 3/3 → 0/3 | ✅ fixed |
| H2 | edge | 83% → 100% | 100% → 100% | 99% → 99% | 3.2 s → 2.0 s | 1/3 → 1/3 | ❌ worse |
| H3 | adversarial | 100% → 100% | 100% → 100% | 100% → 100% | 2.6 s → 2.8 s | 0/3 → 0/3 |  |
| H4 | edge | 83% → 100% | 100% → 100% | 97% → 98% | 2.8 s → 1.8 s | 1/3 → 1/3 |  |
| H5 | happy-path | 100% → 100% | 100% → 100% | 100% → 100% | 1.7 s → 1.5 s | 0/3 → 0/3 |  |

## Fixed (1)

H1

## Worse (1)

Every case where a measure's average dropped, with the explanation from the after experiment's first failing run.

**H2**: Does MiColab have any flaws that attackers are exploiting in the wild?

- Faithful: facts: 99% → 99%. 24 supported, 1 unsupported, 1 guidance. Unsupported: CVE-2022-26143 affects MiCollab before 9.4 SP1 FP1. (Source says 'before 9.4 SP1 FP1' but also lists '9.4' and '9.4 sp1' as affected; 'before 9.4 SP1 FP1' is imprecise compared to source listing specific versions.)

