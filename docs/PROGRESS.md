# Progress

| Phase | Focus | Checkpoint | Status |
|---|---|---|---|
| 0 | Project, CallGuard baseline tag, setup check | Every check passes; repository on GitHub | **Done** 2026-10-31 (8/8 checks) |
| 1 | 40-case golden dataset | All 40 verified against the data and uploaded to LangSmith | **Done** 2026-10-31 (40/40 checked; `callguard-golden-40` tagged `v1`) |
| 2 | Evaluators and the baseline run | Baseline experiment in LangSmith, results by group | |
| 3 | Failure clusters | Clusters written up; fixes approved | |
| 4 | Fixes and the re-run | After-fix experiment and the comparison | |
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

## Found in Phase 0

- **The index is complete:** 895 entries, each identical to its record. `index_info.json` says 889 because it's written only on a full rebuild; the syncs since then added 6.
- **CallGuard's scheduled sync has been failing since 2026-10-22.** It still points at the folder's old name (`RAG2`), so every run stops with "No such file or directory". It changes nothing, so the data has stayed at 2026-10-20 18:44 UTC, which is what the evaluation needs. After the evaluation, run `uv run scripts/schedule_sync.py on` inside `CallGaurd` to point it at the right folder.
