# Failure clusters (Phase 3)

From the baseline [`baseline-eb9d5153`](baseline-eb9d5153.md): CallGuard `v1.0-baseline`, 40 cases × 3 runs, scored after the evaluator calibration in Phase 2. Every failing run was traced to a cause, using the LangSmith traces, CallGuard's code and the search index. The search ranks quoted below are measured, not guessed.

## Summary

| # | Cluster | Cases (failing runs) | What fails | Root cause | Proposed fix |
|---|---|---|---|---|---|
| 1 | Slow answers | 15 of 120 runs over 6 s; p95 7.2 s | p95 under 6 s ❌ | Writing takes 99% of the time, and half of the writer's output tokens are hidden reasoning | **F1** Writer without hidden reasoning |
| 2 | "List every…" capped at 8 | L1 (3/3) | 8 of 13 CVEs; the answer says the data has "only eight" | The filters find exactly the 13 right records; the final cut keeps 8 | **F2** List mode: every matching record, with the count |
| 3 | Noisy questions lose records | X1 (3/3), A2 (3/3) | 4 of 5 and 2 of 5 CVEs | "Asterix" matches no product filter; A2's markup yields a fake version "1.0" that reorders results | **F3** Clean the question; tolerate a misspelled product name |
| 4 | Versions only in the description | V3 (3/3) | The answer hedges on CVE-2025-52913 | No structured version data, so code says "unknown" and the writer, as instructed, only quotes the description | **F4** Read version ranges from the description in code (and accept a "v" prefix) |
| – | Ranking miss, not fixed | S2 (3/3) | 5 of 7 CVEs | The two missed records rank 13th and 39th for this wording | None proposed (see below) |
| – | Judge noise, not fixed | S3 (1/3) | One "partly" | The judge wanted the reference's remark about Verint and Avaya repeated | None needed |

Measurement clusters found and fixed in Phase 2 (before the baseline was accepted): the correctness judge couldn't see the records, the refusal wording missed "does not appear", and strict faithfulness counts safety caveats as unsupported (so a facts-only score sits next to it). See the baseline report's measurement audit.

**Dropped from the plan:** the prompt-injection guardrail. Both attacks were resisted in all 6 runs (nothing they asked for appeared, no invented citation, the real question answered), so there is nothing for a guardrail to fix. Input clean-up (F3) is kept, because A2's malformed input did cost it 3 of 5 records.

## 1. Slow answers (latency)

Where the time goes, from the 120 traced runs:

| Step | p50 | p95 | Max |
|---|---|---|---|
| understand (code) | 0.00 s | 0.00 s | 0.01 s |
| retrieve (search, version checks) | 0.05 s | 0.09 s | 0.16 s |
| check (model, open-ended questions only) | 0.00 s | 0.00 s | 1.35 s |
| **write (DeepSeek-V4.1-Flash)** | **3.53 s** | **7.13 s** | **8.31 s** |

- The writer's output is 540 tokens at p50, up to 1,695. Comparing output tokens with the visible answer's length, **about half are hidden reasoning** (the model thinks before writing).
- The slowest answers are the longest: list answers (M5, S2, L1) and long lookups.
- **Why slower than Week 3** (p95 4.6 s, measured the same way): Nebius is slower today (910 tokens/s against 1,182 for the same questions) and answers are slightly longer (median 1,108 characters against 1,037). CallGuard can't change Nebius's speed, only how much it asks the model to produce.
- **Test on L1's real prompt** (two tries each):

| Writer setting | Time | Output tokens | Answer length | CVEs cited |
|---|---|---|---|---|
| As CallGuard runs it | 7.1 s, 7.3 s | 1,013, 1,131 | 2,197, 2,699 chars | 9, 9 |
| `chat_template_kwargs: {"thinking": false}` | **3.7 s, 3.9 s** | 735, 724 | 2,275, 2,228 chars | 9, 10 |
| `enable_thinking: false` | 9.1 s, 6.8 s | 1,201, 1,070 | | 9, 9 (still thinks) |
| `reasoning_effort: low` | 7.8 s, 7.7 s | 1,105, 1,132 | | 8, 8 (still thinks) |

**F1: writer without hidden reasoning.** Pass `chat_template_kwargs: {"thinking": false}` on the writer's calls (`callguard/answer.py`, both the normal and the streaming call). Expected: write time about halved, p95 under 6 s. **Risk:** the reasoning may have been helping it follow the 11 rules (patch order, version checks, refusals). Phase 4 measures exactly that: correctness, faithfulness, refusals and citations on all 40 cases. If quality drops, F1 is reverted and the trade-off reported.

## 2. "List every…" questions capped at 8

- **L1** "List every critical vulnerability in Mitel MiCollab.": the filters (MiCollab + Critical) match exactly the 13 right records, and search ranks all 13 in positions 1–13. The call flow then keeps the first 8 (`SEARCH_K = 8`). The answer lists 8 and, in all three runs, says the data contains only eight, which is false.
- **Side effects of a fix, checked:** among the 40 questions, the ones that ask for a list or narrow by severity, exploitation or ransomware (V4, V5, M1, M2, M5, R2, L1) match 0–7 records, except L1 (13). So a list mode changes only L1.

**F2: list mode.** When a search question (no CVE number, not a priority or newest question) asks for a list ("list", "every", "all … vulnerabilities") or is narrowed by severity, exploitation or ransomware, pass on every record that matches the filters, up to 20, instead of the top 8. The writer is told how many records match, so it never claims "only eight" again; above 20, it is told it sees the 20 most relevant of N. Code: `callguard/understand.py` (the list intent), `callguard/retrieve.py` and `callguard/graph.py` (how many records), `callguard/answer.py` (the count note). Expected: L1 13 of 13. **Risk:** longer list answers take longer to write (F1 offsets this); nothing else changes on this dataset.

## 3. Noisy questions lose records

- **X1** "Has Asterix had any SQL injection vulnerabilities?": "Asterix" matches no product name, so search runs over all 895 records, and FreePBX and Genesys SQL-injection flaws crowd in. CVE-2022-26651, the most serious, ranks 10th. Spelled "Asterisk", the product filter applies and all 5 rank in the top 5.
- **A2** (malformed input): search alone ranks all 5 SSRF CVEs in the top 8. But CallGuard read `version="1.0"` out of `<?xml version="1.0"?>`, checked every Finesse record against "1.0", and moved the "affected" ones (old flaws whose ranges start at 1.x) above the SSRF records, three of which dropped out. With the question cleaned up (Unicode normalised, control characters and markup tags removed, long repeated runs collapsed), no version is found and all 5 rank in the top 6.
- The attack itself failed both times: nothing it asked for appeared, so this is about not losing the real question in the noise.

**F3: clean the question, and tolerate a misspelled product.** Before understanding and search: normalise Unicode (full-width "ＦＩＮＥＳＳＥ" becomes "FINESSE"), drop control and invisible formatting characters, remove markup tags, collapse long runs of one character, and cap the length. Then, only when no product or vendor matched exactly, match a question word to a product name that is spelled almost the same (similarity of 0.8 or more, same first letter, names of 6 letters or more), and tell the writer, so the answer can say "assuming you mean Asterisk". Checked against all 40 questions: the misspelling rule matches only X1. Code: `callguard/understand.py`. Expected: X1 5 of 5, A2 5 of 5. **Risk:** a false product match on some other question; the rule is narrow and the writer is told it was a guess.

## 4. Versions only in the description

- **V3** "We upgraded MiCollab to 9.8.2.0. Are we still affected by CVE-2024-41713?": correctly "no" for CVE-2024-41713, but CVE-2025-52913 has no structured version data. Code marks it "unknown", and the writer, following its rule 5 ("if a check says unknown, say the versions appear only in the description and quote that part"), hedges instead of saying that "through 9.8 SP2 (9.8.2.12)" includes 9.8.2.0.
- Only **7 of 895 records** have no structured versions; all 7 state a range in the description ("through 10.2.0.3", "before 4.2.2.11", "through 9.8 SP2 (9.8.2.12)").
- Related, found in Phase 1: "v9.8.1.201" isn't read as a version at all (X2 still answered correctly, because the writer read the range itself).

**F4: version ranges from the description, in code.** When a record has no structured version data, read "through / up to and including / before / prior to X" next to the product's name in the description, preferring the exact build in brackets, and check the version against it, labelled "from the description". Accept a leading "v" in versions. Code: `callguard/versions.py`, `callguard/understand.py`. Expected: V3 correct in all runs. **Risk:** small (7 records); if the product's name isn't next to a range, the check stays "unknown".

## Not fixed

- **S2** "Is there a way to read or change files on a MiCollab server without logging in?": CVE-2021-27402 ranks 13th and CVE-2025-52913 39th among MiCollab's 50 records for this wording, so neither a list mode nor a few more records reaches them. Fixing it would need query rewriting into the flaw type ("path traversal"), which the Week 3 check-and-rephrase step does only for questions that name no product; extending it to every product question cost time without finding more in Week 3. Kept as a known failure, reported honestly.
- **Faithfulness nits** (9 of 114 written answers, one unsupported claim each): mostly the writer summarising a list of exact builds as a range ("12.6(1) through 12.6(2) and later ES builds"). Minor and not clustered enough to fix now.

## How Phase 4 will check the fixes

- Each fix is a general rule, not tuned to a case; the side-effect checks above were done on all 40 questions.
- The same 40 cases, 3 repetitions, same judge and dataset version `v1`, CallGuard tagged `v1.1`; a per-case and per-measure comparison with the baseline, regressions called out, and changes read against the baseline's own run-to-run spread.
- 5 fresh questions the fixes have never seen, written after the fixes, as a check for overfitting.
