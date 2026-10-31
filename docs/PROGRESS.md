# Progress

| Phase | Focus | Checkpoint | Status |
|---|---|---|---|
| 0 | Project, CallGuard baseline tag, setup check | Every check passes; repository on GitHub | **Done** 2026-10-31 (8/8 checks) |
| 1 | 40-case golden dataset | All 40 verified against the data and uploaded to LangSmith | |
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

## Found in Phase 0

- **The index is complete:** 895 entries, each identical to its record. `index_info.json` says 889 because it's written only on a full rebuild; the syncs since then added 6.
- **CallGuard's scheduled sync has been failing since 2026-10-22.** It still points at the folder's old name (`RAG2`), so every run stops with "No such file or directory". It changes nothing, so the data has stayed at 2026-10-20 18:44 UTC, which is what the evaluation needs. After the evaluation, run `uv run scripts/schedule_sync.py on` inside `CallGaurd` to point it at the right folder.
