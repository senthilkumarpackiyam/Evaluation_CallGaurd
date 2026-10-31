"""Run CallGuard on the golden dataset in LangSmith and score every answer.

  uv run scripts/run_experiment.py --name baseline                         # all 40 cases, 3 repetitions
  uv run scripts/run_experiment.py --name smoke --cases E1,A2 --repetitions 1

One client.evaluate() call. Questions are asked one at a time, so response times aren't distorted by parallel calls.
Right after each answer, the code evaluators (CVEs found and cited, citations, refusals, response time, attacks) and
the two LLM judges (faithfulness, correctness; side by side) score that exact run. Then every run and score is saved
to results/<experiment>.jsonl, and LangSmith's copy of the scores is checked against it.
Refuses to run if CallGuard has unsaved changes, since the result couldn't be traced back to a version.
"""

import argparse
import sys
import time

from langsmith import Client

from callguard_eval.dataset import DATASETS
from callguard_eval.evaluators import CODE_EVALUATORS, JUDGE_MODEL, JUDGES, timing
from callguard_eval.results import langsmith_differences, rows_from, save
from callguard_eval.target import describe, make_target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="experiment prefix, e.g. baseline or after-fixes")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--dataset", default="golden", choices=DATASETS, help="golden (40 cases) or holdout (5)")
    parser.add_argument("--dataset-version", default="v1")
    parser.add_argument("--cases", help="only these case IDs, comma-separated (for a quick check)")
    args = parser.parse_args()

    about = describe()
    if about["callguard"].endswith("+changes"):
        sys.exit(f"CallGuard has unsaved changes ({about['callguard']}): commit them first, so the result can be "
                 "traced back to a version")
    DATASET_NAME = DATASETS[args.dataset]["name"]
    client = Client()
    examples = list(client.list_examples(dataset_name=DATASET_NAME, as_of=args.dataset_version))
    if args.cases:
        wanted = set(args.cases.split(","))
        examples = [e for e in examples if e.metadata["case_id"] in wanted]
    metadata = {**about, "dataset": DATASET_NAME, "dataset_version": args.dataset_version, "judge": JUDGE_MODEL,
                "repetitions": args.repetitions, "cases": len(examples)}
    print(f"{args.name}: CallGuard {about['callguard']}, {len(examples)} cases x {args.repetitions} on "
          f"{DATASET_NAME} {args.dataset_version}", flush=True)

    started = time.time()
    evaluated = client.evaluate(
        make_target(), data=examples, evaluators=CODE_EVALUATORS + JUDGES, summary_evaluators=[timing],
        experiment_prefix=args.name, metadata=metadata, max_concurrency=0, num_repetitions=args.repetitions,
        description=f"CallGuard {about['callguard']} on {DATASET_NAME} {args.dataset_version}, "
                    f"{args.repetitions} repetitions; judge {JUDGE_MODEL}")
    experiment = evaluated.experiment_name
    print(f"1. Answered and scored in {time.time() - started:.0f} s: {experiment}", flush=True)

    project = client.read_project(project_name=experiment)
    rows = rows_from(evaluated, project)
    path = save(rows, experiment)
    errors = sum(1 for r in rows for k, v in r["scores"].items() if v is None)
    print(f"2. Saved {len(rows)} runs to {path.relative_to(path.parents[1])} ({errors} evaluator errors)", flush=True)

    client.flush()
    time.sleep(15)  # LangSmith stores feedback in the background
    differences = langsmith_differences(client, rows)
    print("3. LangSmith's scores match the saved ones" if not differences else
          "3. LangSmith's scores differ from the saved ones (the saved ones are the evaluator's own results): "
          + ", ".join(f"{n} {what}" for what, n in differences.items()))
    print(f"Open it: {project.url}")


if __name__ == "__main__":
    main()
