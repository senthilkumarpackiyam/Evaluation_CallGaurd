"""Score an experiment's saved answers again, without asking CallGuard anything: after an evaluator is corrected, or
to fill in a judge score that failed. Every score is attached to its exact run by ID, in the local results and in
LangSmith.

  uv run scripts/rescore.py baseline-eb9d5153                       # only fill in missing judge scores
  uv run scripts/rescore.py baseline-eb9d5153 --code                # recompute every code evaluator
  uv run scripts/rescore.py baseline-eb9d5153 --judge correctness   # re-judge every run (or faithfulness, or all)

The judges need the writer's full prompt, which only LangSmith keeps, so the runs are read back from there first.
"""

import argparse
import inspect
import time
from concurrent.futures import ThreadPoolExecutor

from langsmith import Client

from callguard_eval.dataset import load_cases, to_example
from callguard_eval.evaluators import CODE_EVALUATORS, correctness, faithfulness
from callguard_eval.results import langsmith_differences, load, repair_langsmith, replace_scores, save


def as_list(outcome):
    return outcome["results"] if "results" in outcome else [outcome]


def code_scores(row, example):
    """Every code evaluator on a saved run, called with the arguments it asks for."""
    available = {"inputs": example["inputs"], "outputs": row["outputs"], "reference_outputs": example["outputs"]}
    scored = []
    for evaluator in CODE_EVALUATORS:
        wanted = inspect.signature(evaluator).parameters
        scored += as_list(evaluator(**{name: available[name] for name in wanted}))
    return scored


def judge_scores(run, example, which):
    scored = []
    if "faithfulness" in which:
        scored += as_list(faithfulness(run.outputs))
    if "correctness" in which:
        scored += as_list(correctness(run.inputs, run.outputs, example["outputs"]))
    return scored


def missing_judges(row):
    which = [] if row["scores"].get("correctness") is not None else ["correctness"]
    if row["outputs"].get("kind") == "answer" and row["scores"].get("faithfulness_facts") is None:
        which.append("faithfulness")
    return which


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment")
    parser.add_argument("--code", action="store_true", help="recompute every code evaluator")
    parser.add_argument("--judge", choices=["correctness", "faithfulness", "all"], help="re-judge every run")
    parser.add_argument("--at-once", type=int, default=8)
    args = parser.parse_args()
    client = Client()
    rows = load(args.experiment)
    examples = {c["id"]: to_example(c) for c in load_cases()}
    # All runs in one listing (reading them one by one, 8 at a time, hit LangSmith's rate limit)
    runs = {str(r.id): r for r in client.list_runs(project_name=args.experiment, is_root=True)}
    work = []  # (row, function giving its new scores)
    for row in rows:
        example = examples[row["case_id"]]
        which = (["correctness", "faithfulness"] if args.judge == "all" else [args.judge]) if args.judge \
            else ([] if args.code else missing_judges(row))
        if args.code:
            work.append((row, lambda row=row, example=example: code_scores(row, example)))
        if which:
            work.append((row, lambda row=row, example=example, which=which: judge_scores(runs[row["run_id"]], example, which)))
    print(f"{args.experiment}: rescoring {len(work)} items")

    with ThreadPoolExecutor(args.at_once) as pool:
        outcomes = list(pool.map(lambda item: (item[0], item[1]()), work))
    changed = 0
    for row, scored in outcomes:
        new = [s for s in scored if row["scores"].get(s["key"]) != s["score"]
               or row["comments"].get(s["key"], "") != (s["comment"] or "")]
        for s in scored:
            before = row["scores"].get(s["key"])
            if before != s["score"]:
                print(f"  {row['case_id']} run {row['repetition']}: {s['key']} {before} -> {s['score']}")
            row["scores"][s["key"]] = s["score"]
            row["comments"][s["key"]] = s["comment"] or ""
        row["scores"].pop("judges", None)  # a judge that raised was recorded under the evaluator's own name
        row["comments"].pop("judges", None)
        if new:
            replace_scores(client, row["run_id"], new)
            changed += 1
    save(rows, args.experiment)
    print(f"Saved; {changed} runs had a score or explanation change")

    client.flush()
    time.sleep(10)
    added, removed = repair_langsmith(client, rows)
    if added or removed:
        print(f"LangSmith: {added} missing scores added, {removed} copies removed")
        client.flush()
        time.sleep(10)
    differences = langsmith_differences(client, rows)
    print("LangSmith's scores match the saved ones" if not differences else f"Still different: {dict(differences)}")


if __name__ == "__main__":
    main()
