# Roadmap

Track 3: evaluate CallGuard (the Week 3 RAG agent) with LangSmith. Deadline Sunday 1 November 2026. Each phase starts only after approval, and ends with a summary of what was done.

## How the work is organised

| Item | Choice | Why |
|---|---|---|
| This repository | The dataset, evaluators, runs, results and reports. One commit per phase | Same pattern as the earlier projects |
| Fixes | Made in CallGuard itself, on its `evaluation` branch: `v1.0-baseline` before, `v1.1` after | The agent's code lives there; `main` stays as submitted. Every experiment records which CallGuard it ran |
| Connection | CallGuard (`../CallGaurd`) is an editable dependency | Keys stay in CallGuard's `.env`; nothing is copied |
| Data | Frozen at the last sync, 2026-10-20 18:44 UTC (committed on the `evaluation` branch) | Before and after must see identical data, or the deltas mean nothing |

## Phase 0: Set up (~45 min)

- uv project, README, this roadmap, [progress](docs/PROGRESS.md)
- CallGuard: commit the data snapshot on an `evaluation` branch and tag it `v1.0-baseline`
- Setup check: Python, CallGuard version, keys (names only), Nebius models, LangSmith, data, index, one traced question
- **Done when:** every check passes and the repository is on GitHub

## Phase 1: The 40-case golden dataset (~2 h)

| Group | Count | From |
|---|---|---|
| Happy path | 20 | 13 clean passes from the 25-question exam (E1–4, V1, V2, V4, V5, S4, S5, M2, M3, F2) + 7 new across more products |
| Edge | 12 | 7 from the exam (V3, M4, F1, R2–R5) + 5 new: misspelled product, odd version formats, a CVE that doesn't exist, two CVEs in one question, a lower-case CVE ID |
| Known failure | 6 | S1, S2, S3, M1, R1 (CallGuard's failure analysis) + 1 new "list everything" question |
| Adversarial | 2 | A prompt injection and a malformed input |

- Each case: group, expected behaviour (answer, refuse or resist), expected CVEs, phrases that must not appear, and a reference answer
- A script checks every expected CVE against the data
- Uploaded to LangSmith as `callguard-golden-40`, one split per group; a JSONL copy lives in this repository
- **Done when:** all 40 pass the check and are in LangSmith

## Phase 2: Evaluators and the baseline (~2 h)

- **Code evaluators:** CVE recall (found and cited), citation validity, refusal correctness (both directions), latency (per answer, p50/p95), injection resisted
- **LLM judges:** faithfulness and correctness against the reference, by a different model from the writer
- `client.evaluate()` over all 40 cases, **3 repetitions**, so run-to-run noise is known before deltas are read
- **Done when:** the baseline experiment is in LangSmith, with a results table by group

## Phase 3: Failure clusters (~1 h)

- Group every baseline failure by cause: retrieval miss, refusal wording, metric artifact, injection, latency, malformed input
- Candidate fixes, chosen from what the baseline shows:
  1. List-all retrieval for "list every…" questions
  2. Rephrase plain wording into the flaw type before searching
  3. An injection guardrail with input clean-up
  4. Refusal-aware faithfulness: a metric fix, reported next to the strict score, never instead of it
- **Approval needed** on which fixes go in

## Phase 4: Fix and re-run (~3 h)

- Build the fixes in CallGuard, with tests (the existing 37 must still pass)
- Re-run the same 40 cases with the same settings, 3 repetitions; compare the experiments in LangSmith
- A change table for each case and each measure, with any regressions called out
- Overfitting guard: fixes are general rules, and 5 fresh questions they never saw are checked
- **Done when:** the after-fix experiment and the comparison exist

## Phase 5: Deliverables (~2–3 h)

- Spreadsheet (.xlsx): a summary, plus all 40 cases with baseline and after scores, the change, failure cluster, fix and LangSmith links
- Evaluation report: method, dataset design, baseline, clusters, fixes, changes, limitations
- Loom script: about 5 minutes, timed, with what to show in LangSmith
- Final README, push, and the `v1.1` tag

**Total: about 11–13 hours.** Risks: slow Nebius answers skew latency (3 repetitions help); the judge varies by about ±3 points; the deadline is tight.
