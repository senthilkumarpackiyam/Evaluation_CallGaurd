"""Phase 5: the spreadsheet of every case and run, built from the saved results (no model calls).

Run it with:  uv run scripts/build_spreadsheet.py
Writes reports/callguard_evaluation.xlsx:
- Summary: every measure for the baseline, v1.1 and the final v1.2, against the targets, by group, and the held-out
  check. Formulas over the All runs sheet, so they follow the data.
- Golden cases: the 40 cases, baseline vs final, with cluster, fix, the judge's note and LangSmith links.
- Held-out: the 5 cases written after the fixes, on v1.0-baseline, v1.1 and v1.2.
- All runs: every run of the six experiments with every score: the data the other sheets compute from.
"""

import statistics

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from callguard_eval import ROOT
from callguard_eval.dataset import load_cases
from callguard_eval.results import load
from callguard_eval.summary import run_failures

from callguard.evaluate import p95  # noqa: E402

OUT = ROOT / "reports" / "callguard_evaluation.xlsx"
GOLDEN = [("baseline-eb9d5153", "v1.0-baseline", "Baseline (v1.0)"),
          ("after-fixes-f943ddf3", "v1.1", "v1.1 (F1–F4)"),
          ("after-guard-404070fe", "v1.2", "Final v1.2 (F1–F5)")]
HOLDOUT = [("holdout-v1.0-baseline-1660472b", "v1.0-baseline", "Baseline (v1.0)"),
           ("holdout-v1.1-0dcacb62", "v1.1", "v1.1 (F1–F4)"),
           ("holdout-v1.2-86e64089", "v1.2", "Final v1.2 (F1–F5)")]
UNTRACED = {"holdout-v1.2-86e64089"}  # run after LangSmith's monthly trace limit was reached: no runs stored there
# From reports/failure_clusters.md
CLUSTER = {"L1": ("“List every…” capped at 8", "F2 list mode"),
           "X1": ("Noisy question (misspelled product)", "F3 clean question + spelling"),
           "A2": ("Noisy question (malformed input)", "F3 clean question + spelling"),
           "V3": ("Versions only in the description", "F4 description versions"),
           "M5": ("Slow answers", "F1 writer without reasoning"),
           "S2": ("Ranking miss (not fixed)", "–"),
           "S3": ("Judge noise (not fixed)", "–"),
           "H1": ("Held-out: list mode", "F2"), "H2": ("Held-out: misspelling", "F3"),
           "H3": ("Held-out: malformed input", "F3"), "H4": ("Held-out: description versions", "F4"),
           "H5": ("Held-out: everyday question", "–")}
SCORES = [("correctness", "Correct (judge)"), ("faithfulness_facts", "Faithful: facts"),
          ("faithfulness_strict", "Faithful: strict"), ("cves_found", "CVEs found"), ("cves_cited", "CVEs cited"),
          ("citations_valid", "Citations valid"), ("refusal_correct", "Refusals right"),
          ("attack_resisted", "Attacks resisted"), ("under_6s", "Under 6 s")]
FLAGGED = ["correctness", "faithfulness_facts", "cves_found", "cves_cited", "citations_valid", "refusal_correct",
           "attack_resisted", "under_6s"]  # a run fails if any is below 1 (strict faithfulness is shown, not flagged)

FONT = "Arial"
BODY, BOLD = Font(name=FONT, size=10), Font(name=FONT, size=10, bold=True)
TITLE = Font(name=FONT, size=14, bold=True)
INPUT = Font(name=FONT, size=10, color="0000FF")  # typed-in numbers (blue), as opposed to formulas (black)
LINK = Font(name=FONT, size=10, color="0563C1", underline="single")
HEAD_FILL = PatternFill("solid", fgColor="DCE6F1")
THIN = Border(bottom=Side(style="thin", color="A6A6A6"))
PCT = "0.0%"


def style_header(ws, row, columns):
    for col in range(1, columns + 1):
        c = ws.cell(row=row, column=col)
        c.font, c.fill, c.border = BOLD, HEAD_FILL, THIN
        c.alignment = Alignment(wrap_text=True, vertical="top")


def widths(ws, values):
    for i, w in enumerate(values, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def printable(text):
    return " ".join("".join(ch if ch.isprintable() else " " for ch in text).split())


def all_runs_sheet(wb, experiments):
    ws = wb.create_sheet("All runs")
    header = ["Experiment", "CallGuard", "Dataset", "Case", "Group", "Type", "Repetition", "Route", "Kind", "Seconds",
              *[label for _, label in SCORES], "Failed", "Rewritten by guard", "Judge's note (correctness)",
              "LangSmith run", "Key"]
    ws.append(header)
    style_header(ws, 1, len(header))
    col = {name: i + 1 for i, name in enumerate(header)}
    first_score = col[SCORES[0][1]]
    rows = 0
    for name, version, dataset in experiments:
        for r in load(name):
            rows += 1
            o = r["outputs"]
            line = [name, version, dataset, r["case_id"], r["group"], r["type"], r["repetition"], o.get("route"),
                    o.get("kind"), o.get("seconds"), *[r["scores"].get(key) for key, _ in SCORES], None,
                    o.get("rewritten", 0), (r["comments"].get("correctness") or "")[:300], None,
                    f"{name}|{r['case_id']}"]  # an unambiguous lookup key: as a bare criterion, "M1" was read as a number
            ws.append(line)
            row = ws.max_row
            # Failed: any flagged measure below 1 (blank = the measure doesn't apply to this case)
            checks = ",".join(f"AND(ISNUMBER({get_column_letter(first_score + i)}{row}),"
                              f"{get_column_letter(first_score + i)}{row}<1)"
                              for i, (key, _) in enumerate(SCORES) if key in FLAGGED)
            ws.cell(row=row, column=col["Failed"], value=f"=IF(OR({checks}),1,0)")
            link = ws.cell(row=row, column=col["LangSmith run"])
            if name in UNTRACED:
                link.value = "not stored: LangSmith trace limit"
            else:
                link.value, link.hyperlink, link.font = "open run", r["url"], LINK
            for c in ws[row]:
                if c.font != LINK:
                    c.font = BODY
            for i in range(len(SCORES)):
                ws.cell(row=row, column=first_score + i).number_format = PCT
    ws.freeze_panes = "E2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(header))}{rows + 1}"
    widths(ws, [24, 13, 8, 6, 13, 11, 10, 11, 9, 8] + [10] * len(SCORES) + [7, 9, 60, 11, 28])
    return ws, col, rows + 1


def rng(col, letter_of, last):
    return f"'All runs'!${letter_of[col]}$2:${letter_of[col]}${last}"


def summary_sheet(wb, col, last, golden_rows, holdout_rows):
    ws = wb.active
    ws.title = "Summary"
    L = {name: get_column_letter(i) for name, i in col.items()}
    ws["A1"], ws["A1"].font = "CallGuard evaluation with LangSmith: summary", TITLE
    ws["A2"] = ("40-case golden dataset, every case run 3 times per experiment, same judge (Qwen3.5-397B) and "
                "dataset version v1; only CallGuard changed. Every score is computed by formula from the All runs "
                "sheet; blue numbers are typed in (see their notes).")
    ws["A2"].font = BODY
    ws["A2"].alignment = Alignment(wrap_text=True)
    ws.merge_cells("A2:G2")
    ws.row_dimensions[2].height = 42

    header = ["Measure", "Target", *[label for _, _, label in GOLDEN], "Change (final − baseline)", "Final meets target"]
    ws.append([])
    ws.append(header)
    style_header(ws, 4, len(header))
    ws.append(["Experiment", None, *[name for name, _, _ in GOLDEN]])
    for c in ws[5]:
        c.font = Font(name=FONT, size=9, italic=True, color="595959")
    exp_cells = {name: f"${get_column_letter(3 + i)}$5" for i, (name, _, _) in enumerate(GOLDEN)}

    targets = {"correctness": None, "faithfulness_facts": 0.9, "faithfulness_strict": 0.9, "cves_found": None,
               "cves_cited": None, "citations_valid": 1, "refusal_correct": 0.95, "attack_resisted": 1, "under_6s": None}
    row = 6
    for key, label in SCORES:
        ws.cell(row=row, column=1, value=label)
        if targets[key] is not None:
            t = ws.cell(row=row, column=2, value=targets[key])
            t.font, t.number_format = INPUT, PCT
        for i, (name, _, _) in enumerate(GOLDEN):
            c = ws.cell(row=row, column=3 + i, value=f"=AVERAGEIFS({rng(label, L, last)},{rng('Experiment', L, last)},"
                                                      f"{exp_cells[name]})")
            c.number_format = PCT
        ws.cell(row=row, column=6, value=f"=E{row}-C{row}").number_format = "+0.0%;-0.0%;0.0%"
        if targets[key] is not None:
            ws.cell(row=row, column=7, value=f'=IF(E{row}>=B{row},"✅ met","❌ missed")')
        row += 1
    # Response times: typed in, because CallGuard's nearest-rank percentile differs slightly from Excel's PERCENTILE
    for label, fn, target in [("p50 response time (s)", statistics.median, None), ("p95 response time (s)", p95, 6)]:
        ws.cell(row=row, column=1, value=label)
        if target:
            ws.cell(row=row, column=2, value=target).font = INPUT
        for i, (name, _, _) in enumerate(GOLDEN):
            seconds = [r["seconds"] for r in golden_rows[name]]
            c = ws.cell(row=row, column=3 + i, value=round(fn(seconds), 2))
            c.font, c.number_format = INPUT, "0.0"
            c.comment = Comment(f"Typed in: {label.split(' (')[0]} of the {len(seconds)} runs' seconds in "
                                f"results/{name}.jsonl, nearest rank (callguard.evaluate.p95), as in reports/.",
                                "build_spreadsheet.py")
        ws.cell(row=row, column=6, value=f"=E{row}-C{row}").number_format = "+0.0;-0.0;0.0"
        if target:
            ws.cell(row=row, column=7, value=f'=IF(E{row}<B{row},"✅ met","❌ missed")')
        row += 1
    ws.cell(row=row, column=1, value="Runs")
    for i, (name, _, _) in enumerate(GOLDEN):
        ws.cell(row=row, column=3 + i, value=f"=COUNTIFS({rng('Experiment', L, last)},{exp_cells[name]})")
    row += 1
    ws.cell(row=row, column=1, value="Answers rewritten by the citation guard")
    for i, (name, _, _) in enumerate(GOLDEN):
        ws.cell(row=row, column=3 + i, value=f"=SUMIFS({rng('Rewritten by guard', L, last)},"
                                              f"{rng('Experiment', L, last)},{exp_cells[name]})")
    row += 2

    ws.cell(row=row, column=1, value="By group (golden dataset)").font = BOLD
    row += 1
    g_header = ["Group", "Cases", "Correct: baseline", "Correct: final", "Change", "CVEs found: baseline",
                "CVEs found: final", "Change"]
    for i, h in enumerate(g_header, 1):
        ws.cell(row=row, column=i, value=h)
    style_header(ws, row, len(g_header))
    for group in ["happy-path", "edge", "known-failure", "adversarial"]:
        row += 1
        ws.cell(row=row, column=1, value=group)
        ws.cell(row=row, column=2, value=f'=COUNTIFS({rng("Experiment", L, last)},{exp_cells[GOLDEN[0][0]]},'
                                         f'{rng("Group", L, last)},A{row})/3')
        for c_col, measure, exp in [(3, "Correct (judge)", GOLDEN[0][0]), (4, "Correct (judge)", GOLDEN[2][0]),
                                    (6, "CVEs found", GOLDEN[0][0]), (7, "CVEs found", GOLDEN[2][0])]:
            c = ws.cell(row=row, column=c_col, value=f"=IFERROR(AVERAGEIFS({rng(measure, L, last)},"
                                                     f"{rng('Experiment', L, last)},{exp_cells[exp]},"
                                                     f"{rng('Group', L, last)},$A{row}),\"–\")")
            c.number_format = PCT
        for c_col, a, b in [(5, "D", "C"), (8, "G", "F")]:
            ws.cell(row=row, column=c_col, value=f'=IFERROR({a}{row}-{b}{row},"–")').number_format = "+0.0%;-0.0%;0.0%"
    row += 2

    ws.cell(row=row, column=1, value="Held-out check: 5 cases written after the fixes").font = BOLD
    row += 1
    h_header = ["Measure", None, *[label for _, _, label in HOLDOUT], "Change (final − baseline)"]
    for i, h in enumerate(h_header, 1):
        ws.cell(row=row, column=i, value=h)
    style_header(ws, row, len(h_header))
    row += 1
    ws.cell(row=row, column=1, value="Experiment")
    for i, (name, _, _) in enumerate(HOLDOUT):
        ws.cell(row=row, column=3 + i, value=name)
    for c in ws[row]:
        c.font = Font(name=FONT, size=9, italic=True, color="595959")
    hold_cells = {name: f"${get_column_letter(3 + i)}${row}" for i, (name, _, _) in enumerate(HOLDOUT)}
    for key, label in [("correctness", "Correct (judge)"), ("cves_found", "CVEs found"),
                       ("citations_valid", "Citations valid"), ("under_6s", "Under 6 s")]:
        row += 1
        ws.cell(row=row, column=1, value=label)
        for i, (name, _, _) in enumerate(HOLDOUT):
            ws.cell(row=row, column=3 + i, value=f"=AVERAGEIFS({rng(label, L, last)},{rng('Experiment', L, last)},"
                                                  f"{hold_cells[name]})").number_format = PCT
        ws.cell(row=row, column=6, value=f"=E{row}-C{row}").number_format = "+0.0%;-0.0%;0.0%"
    row += 1
    ws.cell(row=row, column=1, value="p50 response time (s)")
    for i, (name, _, _) in enumerate(HOLDOUT):
        c = ws.cell(row=row, column=3 + i, value=round(statistics.median(r["seconds"] for r in holdout_rows[name]), 2))
        c.font, c.number_format = INPUT, "0.0"
        c.comment = Comment(f"Typed in: median of the runs' seconds in results/{name}.jsonl.", "build_spreadsheet.py")
    row += 2

    notes = [
        "Notes",
        "Definitions: a measure is averaged only over the runs it applies to (blank in All runs = not applicable). "
        "A run 'fails' if any measure except strict faithfulness is below 100%.",
        "Faithful: facts counts the factual claims the writer's sources support; strict also counts safety caveats as "
        "unsupported (as RAGAS does).",
        "The held-out v1.2 run was made after LangSmith's monthly trace limit was reached: its runs and scores are "
        "complete in results/holdout-v1.2-86e64089.jsonl but not stored in LangSmith.",
        "Source: results/*.jsonl in github.com/senthilkumarpackiyam/Evaluation_CallGaurd; the evaluators' own "
        "results from client.evaluate(), checked against LangSmith's copy.",
    ]
    for i, text in enumerate(notes):
        c = ws.cell(row=row + i, column=1, value=text)
        c.font = BOLD if i == 0 else BODY
        if i:
            ws.merge_cells(start_row=row + i, start_column=1, end_row=row + i, end_column=7)
            c.alignment = Alignment(wrap_text=True)
            ws.row_dimensions[row + i].height = 28
    for r in ws.iter_rows(min_row=4):
        for c in r:
            if c.font in (Font(), None) or c.font.name != FONT:
                c.font = Font(name=FONT, size=10, bold=c.font.bold if c.font else False,
                              color=c.font.color if c.font else None)
    widths(ws, [40, 9, 17, 17, 19, 19, 17, 10])
    ws.freeze_panes = "A5"


def cases_sheet(wb, title, cases, experiments, col, last, compare_with):
    ws = wb.create_sheet(title)
    L = {name: get_column_letter(i) for name, i in col.items()}
    (base_name, _, base_label), (final_name, _, final_label) = experiments[0], experiments[-1]
    header = ["ID", "Group", "Type", "Source", "Question", "Expect", "Expected CVEs", "What it tests", "Known issue",
              "Failure cluster", "Fix", f"Correct: {base_label}", "CVEs found: baseline", "Faithful facts: baseline",
              "Failed runs: baseline", f"Correct: {final_label}", "CVEs found: final", "Faithful facts: final",
              "Failed runs: final", "Change in correct", "Status", "Judge's note (final, run 1)", "Baseline run 1",
              "Final run 1"]
    ws.append(header)
    style_header(ws, 1, len(header))
    rows = {name: {(r["case_id"], r["repetition"]): r for r in load(name)} for name, _, _ in experiments}
    for c in cases:
        row = ws.max_row + 1
        cluster, fix = CLUSTER.get(c["id"], ("", ""))
        values = [c["id"], c["group"], c["type"], c["source"], printable(c["question"]),
                  c["expect"] + (f" ({c['reason']})" if c.get("reason") else ""), len(c["cves"]), c["tests"],
                  c.get("known_issue", ""), cluster, fix]
        for i, v in enumerate(values, 1):
            ws.cell(row=row, column=i, value=v)

        # Matched on the Key column ("<experiment>|<case>"): a bare case ID like "M1" as a criterion was read as a
        # number by one formula engine, which made M1 to M5 match each other
        def avg(measure, exp):
            return f"=IFERROR(AVERAGEIFS({rng(measure, L, last)},{rng('Key', L, last)},\"{exp}|\"&$A{row}),\"–\")"

        def failed(exp):
            return f"=SUMIFS({rng('Failed', L, last)},{rng('Key', L, last)},\"{exp}|\"&$A{row})"

        for i, formula in enumerate([avg("Correct (judge)", base_name), avg("CVEs found", base_name),
                                     avg("Faithful: facts", base_name), failed(base_name),
                                     avg("Correct (judge)", final_name), avg("CVEs found", final_name),
                                     avg("Faithful: facts", final_name), failed(final_name)], 12):
            cell = ws.cell(row=row, column=i, value=formula)
            if i not in (15, 19):
                cell.number_format = PCT
        ws.cell(row=row, column=20, value=f'=IFERROR(P{row}-L{row},"–")').number_format = "+0%;-0%;0%"
        ws.cell(row=row, column=21, value=(f'=IF(AND(O{row}>0,S{row}=0),"fixed",IF(S{row}<O{row},"better",'
                                           f'IF(S{row}>O{row},"more failing runs",IF(S{row}=0,"passes",'
                                           f'"still failing"))))'))
        first_final = rows[final_name].get((c["id"], 1))
        ws.cell(row=row, column=22, value=(first_final["comments"].get("correctness") or "")[:300] if first_final else "")
        for col_no, name in [(23, base_name), (24, final_name)]:
            run = rows[name].get((c["id"], 1))
            cell = ws.cell(row=row, column=col_no)
            if name in UNTRACED:
                cell.value = "not stored (trace limit)"
            elif run:
                cell.value, cell.hyperlink = "open run", run["url"]
        for cell in ws[row]:
            cell.font = LINK if cell.hyperlink else BODY
            cell.alignment = Alignment(wrap_text=cell.column in (5, 8, 9, 22), vertical="top")
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(header))}{ws.max_row}"
    widths(ws, [5, 12, 11, 7, 48, 16, 9, 34, 30, 24, 22, 11, 11, 11, 9, 11, 11, 11, 9, 9, 15, 48, 10, 10])
    note_row = ws.max_row + 2
    ws.cell(row=note_row, column=1, value=(
        f"Status counts failing runs ({compare_with}): fixed = failing runs before, none after. Every measure that "
        "dropped is listed in the comparison report. Scores are averages over the case's 3 runs, from All runs.")).font = BODY
    return ws


def main():
    golden_rows = {name: [r["outputs"] for r in load(name)] for name, _, _ in GOLDEN}
    holdout_rows = {name: [r["outputs"] for r in load(name)] for name, _, _ in HOLDOUT}
    wb = Workbook()
    experiments = [(n, v, "golden") for n, v, _ in GOLDEN] + [(n, v, "holdout") for n, v, _ in HOLDOUT]
    _, col, last = all_runs_sheet(wb, experiments)
    summary_sheet(wb, col, last, golden_rows, holdout_rows)
    cases_sheet(wb, "Golden cases", load_cases("golden"), GOLDEN, col, last, "baseline vs final v1.2")
    cases_sheet(wb, "Held-out", load_cases("holdout"), HOLDOUT, col, last, "v1.0-baseline vs v1.2")
    wb.move_sheet("All runs", offset=3)
    wb.calculation.fullCalcOnLoad = True  # Excel and Google Sheets compute every formula when the file opens
    wb.save(OUT)
    print(f"Wrote {OUT.relative_to(ROOT)}: {last - 1} runs; sheets {wb.sheetnames}")
    # Cross-check used by the verification step: failing runs per experiment, computed here in Python
    for name, _, _ in GOLDEN + HOLDOUT:
        print(f"  {name}: {sum(bool(run_failures(r)) for r in load(name))} failing runs")


if __name__ == "__main__":
    main()
