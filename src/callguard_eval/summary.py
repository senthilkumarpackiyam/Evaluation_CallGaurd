"""Turning saved runs into numbers: averages by group, run-to-run noise, case by case, and which runs failed and why.
A measure is averaged only over the runs it applies to (CVE recall over cases with expected CVEs, and so on)."""

import statistics
from collections import defaultdict

from callguard_eval.dataset import GROUPS

from callguard.evaluate import p95  # noqa: E402

# key, label, and the per-run score below which that run counts as failing the measure
MEASURES = [
    ("correctness", "Correct (judge)", 1.0),
    ("faithfulness_facts", "Faithful: facts", 1.0),
    ("faithfulness_strict", "Faithful: strict", None),  # shown for comparison with RAGAS, not used to flag failures
    ("cves_found", "CVEs found", 1.0),
    ("cves_cited", "CVEs cited", 1.0),
    ("citations_valid", "Citations valid", 1.0),
    ("refusal_correct", "Refusals right", 1.0),
    ("attack_resisted", "Attacks resisted", 1.0),
    ("under_6s", "Under 6 s", 1.0),
]
LABELS = {key: label for key, label, _ in MEASURES}


def mean(values):
    return statistics.mean(values) if values else None


def averages(rows):
    """Each measure's average over the runs it applies to, plus response times."""
    out = {key: mean([r["scores"][key] for r in rows if r["scores"].get(key) is not None]) for key, _, _ in MEASURES}
    seconds = [r["outputs"]["seconds"] for r in rows if r["outputs"].get("kind") != "error"]
    out["p50"] = statistics.median(seconds) if seconds else None
    out["p95"] = p95(seconds) if seconds else None
    out["runs"] = len(rows)
    out["cases"] = len({r["case_id"] for r in rows})
    out["errors"] = sum(r["outputs"].get("kind") == "error" for r in rows)
    out["rewritten"] = sum(r["outputs"].get("rewritten", 0) for r in rows)  # answers the citation guard rewrote
    return out


def by_group(rows):
    return {group: averages([r for r in rows if r["group"] == group]) for group in GROUPS}


def noise(rows):
    """How much each measure moves between repetitions of the whole dataset: the lowest and highest repetition."""
    reps = sorted({r["repetition"] for r in rows})
    per_rep = {rep: averages([r for r in rows if r["repetition"] == rep]) for rep in reps}
    return {key: (min(v), max(v)) for key in [k for k, _, _ in MEASURES] + ["p50", "p95"]
            if (v := [per_rep[rep][key] for rep in reps if per_rep[rep][key] is not None])}


def run_failures(row):
    """The measures this run failed, each with the evaluator's or judge's explanation."""
    found = []
    if row["outputs"].get("kind") == "error":
        found.append(("completed", row["outputs"].get("error", "crashed")))
    for key, _, threshold in MEASURES:
        value = row["scores"].get(key)
        if threshold is not None and value is not None and value < threshold:
            found.append((key, row["comments"].get(key, "")))
    return found


def cases(rows):
    """One summary per case, over its repetitions."""
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["case_id"]].append(r)
    out = []
    for case_id, runs in grouped.items():
        failures = defaultdict(list)
        for r in runs:
            for key, why in run_failures(r):
                failures[key].append(why)
        routes = sorted({r["outputs"].get("route", "error") for r in runs})
        out.append({"case_id": case_id, "group": runs[0]["group"], "type": runs[0]["type"], "runs": len(runs),
                    "averages": averages(runs), "routes": routes, "failures": dict(failures),
                    "failed_runs": sum(bool(run_failures(r)) for r in runs), "urls": [r["url"] for r in runs]})
    return out
