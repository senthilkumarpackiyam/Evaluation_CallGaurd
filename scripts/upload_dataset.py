"""Phase 1: upload the golden dataset to LangSmith as callguard-golden-40, one split per group.

Run it with:  uv run scripts/upload_dataset.py
Refuses to upload if scripts/check_dataset.py would find a problem. Safe to run again: each case keeps a fixed
example ID, so changed cases are updated in place (LangSmith keeps the old version), and nothing is duplicated.
Also writes dataset/golden.jsonl, the exact examples uploaded. The newest version is tagged (default "v1"), so
every experiment can name the dataset version it ran on.
"""

import argparse
import json
import sys
from collections import Counter

from langsmith import Client

from callguard_eval import callguard_version
from callguard_eval.dataset import (DATASET_NAME, EXAMPLES_FILE, GROUPS, load_cases, load_records, problems,
                                    to_example)

from callguard.index import PROCESSED  # noqa: E402

REPOSITORY = "https://github.com/senthilkumarpackiyam/Evaluation_CallGaurd"


def differs(existing, example):
    """Has a case changed since it was uploaded? LangSmith keeps an example's split inside its metadata."""
    metadata = {k: v for k, v in (existing.metadata or {}).items() if k != "dataset_split"}
    return (existing.inputs != example["inputs"] or existing.outputs != example["outputs"]
            or metadata != example["metadata"] or (existing.metadata or {}).get("dataset_split") != [example["split"]])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="v1", help="the name for this version of the dataset in LangSmith")
    args = parser.parse_args()

    cases, records = load_cases(), load_records()
    found = problems(cases, records)
    if found:
        print("Not uploaded: run scripts/check_dataset.py and fix these first:\n" + "\n".join(f"  {p}" for p in found))
        sys.exit(1)
    examples = [to_example(c) for c in cases]
    EXAMPLES_FILE.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in examples))

    client = Client()
    manifest = json.loads((PROCESSED / "manifest.json").read_text())
    if client.has_dataset(dataset_name=DATASET_NAME):
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
    else:
        counts = ", ".join(f"{n} {g}" for g, n in GROUPS.items())
        dataset = client.create_dataset(
            DATASET_NAME,
            description=f"CallGuard's golden dataset: {len(examples)} cases ({counts}). Source: dataset/golden.toml "
                        f"in {REPOSITORY}. Expected answers come from CallGuard's data, frozen at "
                        f"{manifest['collected_at'][:16].replace('T', ' ')} UTC.",
            metadata={"repository": REPOSITORY, "callguard": callguard_version(), "data_as_of": manifest["collected_at"]})

    existing = {str(e.id): e for e in client.list_examples(dataset_id=dataset.id)}
    wanted = {e["id"] for e in examples}
    new = [e for e in examples if e["id"] not in existing]
    changed = [e for e in examples if e["id"] in existing and differs(existing[e["id"]], e)]
    gone = [i for i in existing if i not in wanted]
    if new:
        client.create_examples(dataset_id=dataset.id, examples=new)
    if changed:
        client.update_examples(dataset_id=dataset.id, updates=changed)
    if gone:
        client.delete_examples(gone)
    print(f"{DATASET_NAME}: {len(new)} added, {len(changed)} updated, {len(gone)} removed, "
          f"{len(examples) - len(new) - len(changed)} unchanged")

    uploaded = list(client.list_examples(dataset_id=dataset.id))
    splits = Counter(s for e in uploaded for s in (e.metadata or {}).get("dataset_split", []))
    print(f"In LangSmith: {len(uploaded)} examples; splits " + ", ".join(f"{g} {splits[g]}" for g in GROUPS))
    newest = max(client.list_dataset_versions(dataset_id=dataset.id), key=lambda v: v.as_of)
    if args.tag not in (newest.tags or []):
        client.update_dataset_tag(dataset_id=dataset.id, as_of=newest.as_of, tag=args.tag)
    print(f"Version {newest.as_of:%Y-%m-%d %H:%M:%S} UTC tagged '{args.tag}'")
    print(f"Open it: {dataset.url}")
    print(f"Wrote {EXAMPLES_FILE.relative_to(EXAMPLES_FILE.parents[1])}")


if __name__ == "__main__":
    main()
