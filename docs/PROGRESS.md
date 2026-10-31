# Progress

| Phase | Focus | Checkpoint | Status |
|---|---|---|---|
| 0 | Project, CallGuard baseline tag, setup check | Every check passes; repository on GitHub | **Done** 2026-10-31 (8/8 checks) |
| 1 | 40-case golden dataset | All 40 verified against the data and uploaded to LangSmith | **Done** 2026-10-31 (40/40 checked; `callguard-golden-40` tagged `v1`) |
| 2 | Evaluators and the baseline run | Baseline experiment in LangSmith, results by group | **Done** 2026-10-31 (`baseline-eb9d5153`: 120 runs, 0 errors; [report](../reports/baseline-eb9d5153.md)) |
| 3 | Failure clusters | Clusters written up; fixes approved | **Written** 2026-10-31 ([clusters](../reports/failure_clusters.md)); fixes awaiting approval |
| 4 | Fixes and the re-run | After-fix experiment and the comparison | **Done** 2026-10-31: v1.1 (F1–F4) `after-fixes-f943ddf3`, then v1.2 (+F5) `after-guard-404070fe` ([final comparison](../reports/comparison-final.md), [held-out](../reports/holdout-comparison-final.md)) |
| 5 | Spreadsheet, report, Loom script | Deliverables ready | |

## Decisions log (Phase 0)

| Decision | Choice | Why |
|---|---|---|
| Where the fixes go | CallGuard's `evaluation` branch; `main` stays as submitted | The agent's code lives there, and the submitted version stays untouched |
| Baseline | CallGuard `v1.0-baseline` = `main` plus the data snapshot | Every experiment records the CallGuard version it ran (`callguard_version()`) |
| Data | Frozen at 2026-10-20 18:44 UTC, 895 CVEs | Baseline and after-fix runs must see the same records |
| Keys | Read from CallGuard's `.env`; none in this repository | One place for secrets, never printed |
| Environment | `.venv` is a shortcut to `~/.venvs/callguard-eval` | The project folder is in iCloud, which mishandles virtual environments (CallGuard's Phase 0 finding) |
| Library versions | langsmith, langgraph, langchain-core, openai, qdrant-client and fastembed held at CallGuard's locked versions | uv picked newer ones; the agent should behave exactly as it did when built |
| Judge model (proposed for Phase 2) | `Qwen/Qwen3.5-397B-A17B` | Different from the writer (DeepSeek-V4.1-Flash) and from the checker inside the flow (Qwen3-235B) |

## Decisions log (Phase 1)

| Decision | Choice | Why |
|---|---|---|
| Source of truth | [`dataset/golden.toml`](../dataset/golden.toml), the same format as CallGuard's exam; [`dataset/golden.jsonl`](../dataset/golden.jsonl) is the exact upload | Easy to read and review; the upload can't drift from it (re-uploading reports "40 unchanged") |
| The 25 exam questions | Kept word for word, sorted into groups; only facts the newer data changed were updated (M3: CVE-2025-57819's exploit forecast 86% → 95%; F1 and F2 dated 2026-10-20) | The exam was written before CallGuard was built, which makes it the most honest part of the dataset |
| Known-failure cases | S1, S2, S3, M1, R1 from CallGuard's failure analysis, plus L1 ("list every critical MiCollab CVE": 13 right answers, 8 records per search) | S3, M1 and R1 failed on the *metric*, not the agent; keeping them tests whether the new evaluators are fairer |
| New edge cases | A misspelled product (Asterix), a "v" version prefix, a CVE with two digits swapped, two CVEs in one question, a lower-case CVE ID | Each one was checked against CallGuard's code first: "Asterix" matches no product filter, and "v9.8.1.201" is not read as a version at all |
| Adversarial cases | A1 instruction override with a fake "system update" asking for "safe, no action needed"; A2 771 characters of control codes, markup, SQL, template, JNDI, XML-entity and spreadsheet-formula strings around one real question | The two attack types the brief names: prompt injection and malformed input |
| Expected behaviour | `answer` (32), `refuse` (6, with a reason) or `resist` (2, with `must_not` phrases) | Lets the evaluators score refusals and attacks differently from answers |
| Example IDs | Fixed per case (UUID from the case ID) | Re-uploading updates in place; LangSmith keeps every version |
| Dataset version | Tagged `v1` in LangSmith | Baseline and after-fix experiments both run on `v1`, so any change in scores comes from CallGuard, not from the dataset |

## Decisions log (Phase 2)

| Decision | Choice | Why |
|---|---|---|
| Code evaluators | `completed`, `cves_found`, `cves_cited`, `citations_valid`, `refusal_correct`, `seconds` + `under_6s`, `attack_resisted`; summary: p50, p95, share under 6 s | Everything code can check exactly is checked by code, not by a judge |
| Scope of each measure | An evaluator returns only the scores that apply (no CVE recall for refusals, no refusal score for F1's "none") | Averages aren't diluted by cases a measure doesn't fit |
| Citations | A CVE number the user typed doesn't count as invented when the answer repeats it | X3's correct "no record of CVE-2024-41731" would otherwise look like a made-up citation |
| Refusals | CallGuard's exam wording rules (`callguard.evaluate.REFUSAL_WORDS`), plus one for "unknown cve"; an answer case that is declined is a false refusal | Same yardstick as the Week 3 exam, so the numbers compare |
| LLM judges | `faithfulness` (one judgement, two scores: *facts only* and *strict*) and `correctness` against the reference (correct / partly / wrong = 1 / 0.5 / 0) | Strict reproduces the RAGAS weakness on refusals; facts-only is the fix to the *measure*, always shown next to it |
| What the faithfulness judge sees | The writer's full prompt (instructions with the covered products, the question, the facts code worked out, the records), copied by a recorder in the evaluation harness; CallGuard is unchanged | In the first trial, the judge marked a correct list of covered products as unsupported because it only saw the records |
| Judge model | `Qwen/Qwen3.5-397B-A17B`, temperature 0, **thinking off** (thinking on only as a fallback) | Thinking took 77 s and 11,400 tokens per judgement instead of 9 s, with the same labels except one borderline claim that two thinking runs labelled differently |
| Running | One `client.evaluate()`: questions one at a time (honest response times); right after each answer, the code evaluators and both judges (side by side) score that exact run | The first baseline judged the finished experiment in a second `evaluate()` call. LangSmith matched those scores to runs by example, so with 3 repetitions some runs got 2–3 judge scores and 41 got none. That experiment is renamed `invalid-baseline-1d299497` in LangSmith and not used |
| Source of truth for scores | The evaluator results `evaluate()` returns, saved to `results/<experiment>.jsonl`; LangSmith's copy is then checked against them, reading feedback 20 runs at a time | Reading feedback 100 runs at a time, LangSmith's paging listed 3 of 1,143 items twice and skipped 3, which looked like lost and doubled scores. A "repair" based on that read briefly introduced 8 real errors; with the corrected read they were fixed, and an independent one-run-at-a-time check found every baseline score in LangSmith equal to the saved one (to LangSmith's 4 decimals) |
| A judge reply that can't be read | Ask for strict JSON first; if one judge still fails, keep the other's score; `scripts/rejudge.py` judges the gap again from the saved run | One faithfulness reply (L1, run 3) couldn't be read twice and, in the first version, took that run's correctness with it; re-judged afterwards |
| Repetitions | 3 per case (120 runs), on dataset version `v1` | Shows how much scores move on their own before any change is read as real |

| Evaluator calibration | Every failing verdict read against the records before the baseline was accepted. Two faults corrected, and the same 120 answers scored again with `scripts/rescore.py` (CallGuard not asked again): the correctness judge now sees the writer's sources, and the "unknown cve" refusal wording accepts "does not appear in CallGuard's records" | The judge only saw the reference, so it called correct extra facts "hallucinated" (EPSS scores, a 2026 date it took for the future, four real MiVoice Office 400 CVEs). Correctness 80% → 93%, refusals 98% → 100%; 32 verdicts up, 2 down. First scoring kept in `results/baseline-eb9d5153.judge-v1.jsonl` and shown in the report's audit section |

## Baseline results (Phase 2)

CallGuard `v1.0-baseline`, 40 cases × 3 runs, judge Qwen3.5-397B. [Full report](../reports/baseline-eb9d5153.md).

| Measure | Result | Target |
|---|---|---|
| Correct (judge) | 93% (repetitions 92–94%) | |
| Faithfulness, facts only | 99.6% (9 of 114 written answers had one unsupported claim) | 90% ✅ |
| Faithfulness, strict (RAGAS-style) | 94% (refusals score 68–84%: caveats count against them) | 90% ✅ |
| Expected CVEs found / cited | 96% / 96% | |
| Citations valid | 100% | every one ✅ |
| Refusals right | 100% | 95% ✅ |
| Attacks resisted | 100% (A1 and A2, all runs) | every one ✅ |
| p50 / p95 response time | 3.6 s / 7.2 s (15 of 120 answers over 6 s) | p95 under 6 s ❌ |

What is left, for Phase 3: the remaining "partly" verdicts all fall into four groups. (1) **List questions** capped at 8 records: L1 finds 8 of 13, S2 5 of 7. (2) **Noisy questions lose records**: "Asterix" (X1) misses CVE-2022-26651, and A2's junk finds 2 of 5 (it also read a "version 1.0" out of `<?xml version="1.0"?>`). (3) **Versions only in a description** make the answer hedge (V3, CVE-2025-52913). (4) **Slow answers**, mostly long lists (M5, S2, L1); the Week 3 exam's p95 was 4.6 s, measured the same way.

## Decisions log (Phase 4)

| Decision | Choice | Why |
|---|---|---|
| Fixes approved | F1–F4, all four ([clusters](../reports/failure_clusters.md)) | The brief asks for 3–4; together they cover every agent cluster |
| Where | CallGuard's `evaluation` branch, one commit, tagged `v1.1`; `main` untouched | Every experiment records the version it ran |
| F1 writer without reasoning | `chat_template_kwargs: {"thinking": false}` on both writer calls (normal and streaming) | The only switch that worked (`enable_thinking` and `reasoning_effort` didn't); L1 7.2 s → 3.8 s |
| F2 list mode | Search questions that ask for a list, or that severity, exploitation or ransomware narrows within a product or vendor: every matching record up to 20, and the writer told the count | Only L1 changes on the golden dataset; the count note stops "only eight" |
| F3 clean questions | NFKC, control and format characters, markup tags (`<` + letter, `/`, `!` or `?`, so "versions < 17.0.3" stays), runs of 4+ of one non-digit character, 1,000-character cap; misspelled product only when nothing matched exactly (similarity ≥ 0.8, same first letter, names of 6+ letters) and named to the writer | Narrow enough that real questions, version numbers and CVE numbers pass unchanged (tested) |
| F4 description versions | Used only when the description has exactly one range phrase; 3 of the 7 description-only records qualify, the other 4 stay "unknown" | Several ranges in one sentence ("through 10.0.0.4, 10.1.0.0 through 10.1.0.5, …") are left to people rather than guessed |
| A changed test | `CVE-2025-52913` at 9.8.2.0 was expected "unknown"; it is now "affected" | That is the behaviour F4 is meant to change |
| Overfitting check | `dataset/holdout.toml`: 5 cases written after the fixes, one per fixed behaviour on another product (H1 MiVoice Connect list, H2 "MiColab", H3 HTML email, H4 CVE-2025-27827, H5 Unity Connection), uploaded as `callguard-holdout-5`; run on both `v1.0-baseline` and `v1.1` | A fix that only learned its golden case would show no gain here |
| Comparison | `scripts/compare.py`: a change is "clear" only when the two experiments' repetition ranges don't overlap | The baseline showed correctness moving 92–94% on its own |
| F5 citation guard (approved after the v1.1 run) | A cited CVE number not in the records, and not typed by the user, gets one rewrite naming the wrong number; if one remains, or the answer was streamed, code appends a warning. `Answer.rewritten` counts it. CallGuard `v1.2`, 4 tests (59) | The only regression F1–F4 caused: one invented CVE number in 120 runs. CallGuard detected it but still showed it. Since it happened once in 120, a re-run can't prove the guard works by its absence alone, so the guard is tested with a scripted writer and the re-run counts how often it fired |

## Results after the fixes (Phase 4)

Golden dataset, 40 cases × 3, same judge, evaluators and dataset version; CallGuard `v1.0-baseline` → `v1.1`. [Full comparison](../reports/comparison.md).

| Measure | Baseline | After fixes | |
|---|---|---|---|
| Correct (judge) | 93% (92–94%) | **98%** (98–99%) | ✅ clearly better |
| Expected CVEs found / cited | 96% / 96% | **99.1% / 99%** | ✅ clearly better |
| p50 / p95 response time | 3.6 s / 7.2 s | **2.0 s / 3.6 s** | ✅ clearly better; every answer under 6 s |
| Refusals right · attacks resisted | 100% · 100% | 100% · 100% | |
| Citations valid | 100% | 99.2% (one run) | within noise, but a real error |
| Faithfulness, facts only / strict | 99.6% / 94% | 99.1% / 94% | facts: small, clearly worse |

- **Fixed:** V2, S4, M5, V3, F1, X4, R5, S1, A2 (failed something before, nothing after); L1 and X1 went from 3/3 failing runs to 1/3. Adversarial group 75% → 100% correct.
- **What got worse, honestly:**
  - **One invented CVE number** in 120 runs: S2 run 1 wrote "CVE-2024-41793" for CVE-2024-41713, a digit slip. CallGuard's own citation check flagged it (`unsupported`), but the answer still contained it. Likely a cost of F1 (no reasoning to catch it).
  - **Faithfulness, facts only, 99.6% → 99.1%:** single loose inferences in 7 cases ("you are on the fixed release", "unexploited so far", "clears both"), and one judge error: L1 run 1 scored 77% because the judge listed 17 CVSS scores the answer *left out* as unsupported claims. Not re-judged, to avoid choosing which scores to redo.
  - **M4, one run "partly":** said CVE-2024-55550 chains with two flaws instead of one.
- **Still failing:** S2 (5 of 7: ranking, not fixed by design) and one S3 judge nit.
- **Evaluator correction, applied to both experiments:** the "unknown cve" refusal rule now accepts any sentence that names the asked CVE and denies it, instead of a phrase list (it had missed "No CVE-2024-41731 appears in CallGuard's data"). Baseline: no change; after: X3's two correct refusals counted. Tested both ways (a description of the neighbouring CVE still fails).

Held-out check, 5 fresh cases × 3 on both versions. [Comparison](../reports/holdout-comparison.md).

| Measure | v1.0-baseline | v1.1 | |
|---|---|---|---|
| Correct (judge) | 80% (70–90%) | **100%** | ✅ clearly better |
| Expected CVEs found | 96% | **100%** | ✅ clearly better (H1 list: 80% → 100%) |
| p95 response time | 4.1 s | 8.6 s | within noise, and not caused by the fixes (below) |

- The fixes generalise: H1 (another product's list), H2 (another misspelling), H3 (an HTML email) and H4 (another description-only record) all answer correctly on v1.1.
- **Latency on the held-out run is not a fair comparison:** v1.1 ran first, so its first repetition paid for the new questions' search embeddings (retrieve 0.75–5.9 s instead of 0.05 s); the baseline run reused them. One H3 answer also hit a Nebius slowdown (16.8 s to write 281 tokens). The writer itself took 1.4–2.7 s on v1.1 against 1.5–4.0 s on the baseline.
- **A limitation this exposed:** the golden runs' response times were measured with the question embeddings already cached (the questions had been asked before), so a brand-new question in real use also pays 1–6 s for its embedding. The p95 of 3.6 s is for answering, not for a first-ever question.

## Final results: CallGuard v1.2 (F1–F5)

Golden dataset, 40 cases × 3. [Baseline vs v1.2](../reports/comparison-final.md); [v1.1 vs v1.2](../reports/comparison-guard.md).

| Measure | Baseline (v1.0) | v1.1 (F1–F4) | **v1.2 (F1–F5)** | Baseline → v1.2 |
|---|---|---|---|---|
| Correct (judge) | 93% | 98% | **98%** (96–99%) | ✅ clearly better |
| Expected CVEs found | 96% | 99.1% | **99.1%** | ✅ clearly better |
| Citations valid | 100% | 99.2% | **100%** | |
| Refusals right · attacks resisted | 100% · 100% | 100% · 100% | **100% · 100%** | |
| Faithfulness, facts only | 99.6% | 99.1% | **99.4%** | slightly worse (−0.2 pts) |
| p50 / p95 | 3.6 s / 7.2 s | 2.0 s / 3.6 s | **2.1 s / 3.8 s** | ✅ clearly better; 98% under 6 s |

- **The citation guard didn't fire** in these 120 runs: no answer cited an invented CVE number this time. A 1-in-120 error can't be shown fixed by its absence in one more run, so the guard's evidence is its 4 tests with a scripted writer; this run shows it costs nothing when it isn't needed (v1.1 vs v1.2 within noise on every measure).
- **The 3 answers over 6 s were single stalled Nebius calls**, not CallGuard: M3's writer took 16.7 s for 564 tokens (usually about 2 s), and S3's 54-token check call took 14.6 s and 3.7 s (usually about 1 s). A shorter API timeout with one retry would remove these; noted as a next step, not built.
- **The small price of F1** (no hidden reasoning): faithfulness, facts only, 99.6% → 99.4%, from single loose inferences ("your build is the fixed one", "not applicable" for an Unknown ransomware status) and two one-run "partly" verdicts (V1, M4).
- **Held-out check on v1.2** ([comparison](../reports/holdout-comparison-final.md)): correct 80% → **100%**, CVEs found 96% → **100%**, p50 2.8 s → 2.0 s, every answer under 6 s.

**LangSmith's monthly trace limit was reached** during the held-out run on v1.2 ("Monthly unique traces usage limit exceeded", free plan). Each experiment stores one trace per run plus one per evaluator call, about 1,200 per 120-run experiment.
- Every experiment above except the held-out v1.2 run is complete in LangSmith.
- The held-out v1.2 numbers come from `results/holdout-v1.2-86e64089.jsonl`, the evaluators' own results (complete: 15 runs, all scored, since the judges run on this machine). Its LangSmith experiment is renamed `untraced-holdout-v1.2-86e64089` and holds no runs. An earlier attempt, `incomplete-holdout-v1.2-1395c6d2`, has 14 of its 15 runs in LangSmith (its local file was deleted before the limit was understood).
- **Until the limit resets, nothing new is traced**, including CallGuard's own website and `ask.py`. Next time: `client.evaluate(..., disable_evaluator_tracing=True)` would cut the traces per experiment from about 1,200 to 120.
- `scripts/run_experiment.py` now waits for every trace to be uploaded before reading back (`wait_for_all_tracers`) and adds back any score LangSmith is missing.

## Found in Phase 0

- **The index is complete:** 895 entries, each identical to its record. `index_info.json` says 889 because it's written only on a full rebuild; the syncs since then added 6.
- **CallGuard's scheduled sync has been failing since 2026-10-22.** It still points at the folder's old name (`RAG2`), so every run stops with "No such file or directory". It changes nothing, so the data has stayed at 2026-10-20 18:44 UTC, which is what the evaluation needs. After the evaluation, run `uv run scripts/schedule_sync.py on` inside `CallGaurd` to point it at the right folder.
