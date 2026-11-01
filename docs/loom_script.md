# Loom video: script and recording guide

A 5-minute walkthrough of the CallGuard evaluation in LangSmith: the golden dataset, the evaluators, the baseline, the failure clusters, the fixes and the results. Every number below comes from the saved results and the reports in this repository.

**The video only shows experiments that already ran.** LangSmith's monthly trace limit on this account was reached on 31 October. Nothing new can be traced until it resets, but every experiment shown here was stored before that.

## Before you record (about 10 minutes)

1. **Open these tabs in one Chrome window, left to right, in the order you'll use them.** During the recording, **Ctrl+Tab** moves to the next tab.
   1. **The Google Doc** "Evaluating CallGuard with LangSmith" (the video starts here).
   2. **The dataset:** https://smith.langchain.com/o/f5e8048c-06b9-4337-a12f-0be94abd651f/datasets/ef3e6146-6498-4909-9699-2ab76bd229b7
   3. **The baseline experiment:** https://smith.langchain.com/o/f5e8048c-06b9-4337-a12f-0be94abd651f/projects/p/1c40d7a8-5873-4e19-a690-4fde8aca673b
   4. **R1 in the baseline** (run 1): https://smith.langchain.com/o/f5e8048c-06b9-4337-a12f-0be94abd651f/projects/p/1c40d7a8-5873-4e19-a690-4fde8aca673b/r/01a19271-a00d-77bf-a8f9-4ca5d8d557ef
   5. **The measurement audit:** https://github.com/senthilkumarpackiyam/Evaluation_CallGaurd/blob/main/reports/baseline-eb9d5153.md#measurement-audit
   6. **L1 before the fixes** (baseline, run 1): https://smith.langchain.com/o/f5e8048c-06b9-4337-a12f-0be94abd651f/projects/p/1c40d7a8-5873-4e19-a690-4fde8aca673b/r/01a1926b-3821-79da-947e-3a48385980d4
   7. **The failure clusters:** https://github.com/senthilkumarpackiyam/Evaluation_CallGaurd/blob/main/reports/failure_clusters.md
   8. **The comparison view of baseline and final.** Open the dataset link again, click the **Experiments** tab, tick `baseline-eb9d5153` and `after-guard-404070fe`, and click **Compare**.
   9. **L1 after the fixes** (v1.2, run 1): https://smith.langchain.com/o/f5e8048c-06b9-4337-a12f-0be94abd651f/projects/p/e7cf4f3e-4219-48ae-a051-e7359e9b461b/r/01a192d8-2849-7012-829a-b3472a06e614
   10. **The repository:** https://github.com/senthilkumarpackiyam/Evaluation_CallGaurd
2. **Open the spreadsheet** `reports/callguard_evaluation.xlsx` in Excel, Numbers or Google Sheets, on its **Summary** sheet. It recalculates when it opens.
3. **Check each tab loads while you're signed in to LangSmith.** In tab 6, click the **write** step once, so you know where it is. Then click tab 1 again.
4. **Tidy the screen.**
   - Close other apps.
   - Turn on Do Not Disturb.
   - Hide the bookmarks bar (Cmd+Shift+B).
   - Zoom LangSmith to 90% if the tables are cut off.
5. **Practise once with a timer.** Aim for 4:45.

## How to record with Loom

1. Start Loom and choose **Screen + Camera**, or **Screen only**.
2. Choose the Chrome window, and your microphone.
3. Click **Start recording**, wait for the countdown, then begin.
4. When you finish, click **Stop**. Loom opens the video, where you can trim the start and the end.

**On Loom's free plan, a recording stops at 5:00:** the timer counts down from 5:00. That's why the script aims for 4:45.

## The script

Replace [your name] with your name. The narration is a guide: say it in your own words.

### 0:00–0:25 Introduction

**Show:** tab 1, the Google Doc's first page, with the summary table.

**Say:** "Hi, I'm [your name]. For Week 3 I built CallGuard, an assistant that answers 'are we exposed?' questions about vulnerabilities in contact-center products, from NVD, CISA and FIRST data. For Track 3 I evaluated it properly in LangSmith: a 40-case golden dataset, code evaluators and LLM judges, a baseline, failure clusters, five fixes and a re-run. Correctness went from 93 to 98 percent, and the slowest answers from 7.2 to 3.8 seconds."

### 0:25–1:05 The golden dataset

**Show:**
1. Tab 2, the dataset. Point at the **splits**: happy-path 20, edge 12, known-failure 6, adversarial 2.
2. Click the **adversarial** split, so only 2 examples show. Open **A2**, the one whose input starts with odd symbols, and scroll its input slowly.
3. Point at its reference outputs: `expect: resist`, the expected CVEs, `must_not`.

**Say:** "The 25 questions from my Week 3 exam are here word for word. They were written before CallGuard existed, which keeps them honest. I added 15 more, and checked each edge case against the code first, so every one tests a real gap: a misspelled product, a 'v' in front of a version, a CVE number with two digits swapped. This one is the malformed input: control characters, a script tag, SQL, a fake XML version, all around one real question. Every case says how CallGuard should behave: answer, refuse for a stated reason, or resist an attack. A script checks every expected CVE against the data before anything is uploaded."

### 1:05–1:50 How every answer is scored

**Show:**
1. Tab 3, the baseline experiment. Point at the feedback columns: correctness, faithfulness facts and strict, CVEs found, citations valid, refusals, attacks resisted, seconds.
2. Tab 4, case **R1**, the made-up product. Point at **faithfulness strict 71%** against **facts only 100%** in its feedback.

**Say:** "One client.evaluate call runs all 40 cases, three times each, so I know how much the scores move on their own. Code evaluators check what code can check exactly: were the right CVEs found and cited, is every citation real, did it decline exactly when it should, did it resist the attacks, and how fast was it. Two LLM judges, a different model from CallGuard's own, grade faithfulness and correctness. Faithfulness has two scores. Strict, like RAGAS, counts 'this does not mean it's safe' against the answer, which is why this correct refusal scores 71. Facts-only counts only factual claims: 100."

### 1:50–2:20 Measuring the measure

**Show:** tab 5, the baseline report on GitHub, at **Measurement audit**.

**Say:** "Before I trusted the baseline, I read every failing verdict against the records. The correctness judge had only seen the reference answer, so it called correct facts 'hallucinated', even four real CVEs. I gave it the same sources the writer saw and re-scored the same 120 answers. Correctness went from 80 to 93 percent, and both scorings are in the report. Measuring the measure was the most important step."

### 2:20–3:05 Baseline and failure clusters

**Show:**
1. Tab 6, **L1 before the fixes**. Click **retrieve**, then **write**, and point at the step times.
2. In the output, point at the line where the answer says there are only eight.

**Say:** "The baseline: 93 percent correct, 100 percent on citations, refusals and attacks, but p95 of 7.2 seconds, over the 6-second target. I traced every failure to a cause. This one, 'list every critical MiCollab vulnerability': the filters find exactly the 13 right records, then the search keeps 8, and the answer says the data has only eight. The trace also shows where the time goes: search takes five hundredths of a second, and writing takes seven seconds, half of it the model's hidden reasoning."

### 3:05–3:40 The fixes

**Show:** tab 7, the failure clusters on GitHub, at the summary table.

**Say:** "Four clusters, four fixes:
- Run the writer without hidden reasoning.
- A list mode that passes every matching record and tells the writer the count.
- Clean noisy questions and tolerate a misspelled product.
- Read version ranges from descriptions.

The re-run then caught a regression my own fix caused: once in 120 answers, CVE-2024-41713 came out as 41793. So a fifth fix, a citation guard, rewrites any answer that cites a CVE that isn't in its records."

### 3:40–4:25 After the fixes

**Show:**
1. Tab 8, the comparison view. Point at the averages for correctness, CVEs found and latency.
2. Tab 9, **L1 after the fixes**. Point at the 13 CVEs and the time.

**Say:** "Same dataset, same judge; only CallGuard changed. Correctness 93 to 98 percent, CVEs found 96 to 99, p95 7.2 to 3.8 seconds, and citations, refusals and attacks still 100 percent. A change only counts when the three-run ranges don't overlap, and these don't. L1 now lists all 13 in under three seconds. It wasn't free: faithfulness fell from 99.6 to 99.4 percent without the reasoning, and the report says so. And five fresh questions, written after the fixes on other products, went from 80 to 100 percent, so the fixes generalise."

### 4:25–4:50 Deliverables

**Show:** switch to the spreadsheet (**Cmd+Tab**): the **Summary** sheet, then the **Golden cases** sheet, scrolled across to the **Status** column.

**Say:** "The spreadsheet has every case and all 405 runs. The summary is computed by formula from the run data, so you can check any number. Each case has its cluster, its fix, the judge's note and a link to its LangSmith trace."

### 4:50–5:00 Close

**Show:** back to Chrome (**Cmd+Tab**), tab 10, the GitHub README.

**Say:** "Everything is on GitHub: the dataset, the evaluators, every result and the report. The lesson I'd keep: check your evaluators before you trust their numbers. Thanks for watching."

## If something goes wrong

- **A LangSmith page asks you to sign in:** sign in first, then reload the tab.
- **The comparison view shows other experiments:** untick everything except `baseline-eb9d5153` and `after-guard-404070fe`.
- **You run over time:** shorten "Measuring the measure" to its first and last sentence.
