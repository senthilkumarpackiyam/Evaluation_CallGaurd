"""Experiments kept locally: every run with its outputs and scores in results/<experiment>.jsonl, so reports and the
spreadsheet can be rebuilt without asking CallGuard anything again.

The rows come from what client.evaluate() itself returns: each run with the evaluator results computed on it. That
is the authoritative record; langsmith_differences() checks LangSmith's copy against it, and repair_langsmith()
makes the two match if they don't."""

import json
from collections import Counter, defaultdict

from callguard_eval import ROOT
from callguard_eval.dataset import load_cases

RESULTS_DIR = ROOT / "results"


def rows_from(experiment_results, project):
    cases = {c["id"]: c for c in load_cases()}
    order = {c["id"]: i for i, c in enumerate(load_cases())}
    rows, repetition = [], defaultdict(int)
    for item in sorted(experiment_results, key=lambda item: item["run"].start_time):
        run, case = item["run"], cases[item["example"].metadata["case_id"]]
        repetition[case["id"]] += 1
        scored = item["evaluation_results"]["results"]
        rows.append({"experiment": project.name, "case_id": case["id"], "group": case["group"], "type": case["type"],
                     "expect": case["expect"], "repetition": repetition[case["id"]], "run_id": str(run.id),
                     "url": f"{project.url}/r/{run.id}",
                     # the writer's full prompt stays in LangSmith; it would make this file ten times bigger
                     "outputs": {k: v for k, v in (run.outputs or {}).items() if k != "writer_prompt"},
                     "scores": {r.key: r.score for r in scored},
                     "comments": {r.key: r.comment for r in scored if r.comment}})
    rows.sort(key=lambda r: (order[r["case_id"]], r["repetition"]))
    return rows


def scored_feedback(client, run_ids, batch=20):
    """Every scored feedback item on these runs, each exactly once. Asked about 100 runs at a time, LangSmith's
    paging listed 3 of 1,143 items twice and skipped 3 others; 20 at a time lists each once (checked)."""
    seen = {}
    for i in range(0, len(run_ids), batch):
        for f in client.list_feedback(run_ids=run_ids[i:i + batch]):
            if f.score is not None:
                seen[str(f.id)] = f
    return list(seen.values())


def langsmith_differences(client, rows):
    """Scores that LangSmith holds differently from the local record: missing, there more than once, or a different
    value (LangSmith keeps 4 decimals)."""
    remote = defaultdict(lambda: defaultdict(list))
    for f in scored_feedback(client, [r["run_id"] for r in rows]):
        remote[str(f.run_id)][f.key].append(f.score)
    differences = Counter()
    for row in rows:
        held = remote[row["run_id"]]
        for key, value in row["scores"].items():
            if value is None:
                continue
            if not held[key]:
                differences[f"missing in LangSmith: {key}"] += 1
            elif len(held[key]) > 1:
                differences[f"doubled in LangSmith: {key}"] += 1
            elif round(held[key][0], 4) != round(value, 4):
                differences[f"different in LangSmith: {key}"] += 1
    return differences


def replace_scores(client, run_id, scored):
    """Swap these scores on one run in LangSmith: remove the run's old feedback for each key, then add the new."""
    keys = {s["key"] for s in scored} | {"judges"}  # "judges": a judge that raised, recorded with no score
    for f in client.list_feedback(run_ids=[run_id]):
        if f.key in keys:
            client.delete_feedback(f.id)
    for s in scored:
        if s["score"] is not None:
            client.create_feedback(run_id=run_id, key=s["key"], score=s["score"], comment=s["comment"])


def repair_langsmith(client, rows):
    """Make LangSmith hold exactly the saved scores: add the ones its background upload lost, and remove copies.
    Returns (added, removed)."""
    by_run = defaultdict(lambda: defaultdict(list))
    for f in scored_feedback(client, [r["run_id"] for r in rows]):
        by_run[str(f.run_id)][f.key].append(f)
    added = removed = 0
    for row in rows:
        for key, value in row["scores"].items():
            if value is None:
                continue
            held = by_run[row["run_id"]][key]
            if not held:
                client.create_feedback(run_id=row["run_id"], key=key, score=value, comment=row["comments"].get(key))
                added += 1
            for extra in held[1:]:
                client.delete_feedback(extra.id)
                removed += 1
    return added, removed


def save(rows, experiment):
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{experiment}.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return path


def load(experiment):
    return [json.loads(line) for line in open(RESULTS_DIR / f"{experiment}.jsonl")]
