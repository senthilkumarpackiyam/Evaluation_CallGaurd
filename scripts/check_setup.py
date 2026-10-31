"""Phase 0 setup check: everything the evaluation needs, ending with one real question traced in LangSmith.

Run it with:  uv run scripts/check_setup.py
Checks Python, which CallGuard is being evaluated, the keys (by name only; values are never printed), the Nebius
models, LangSmith, the frozen data and the search index, then asks one question through CallGuard's call flow.
"""

import json
import os
import subprocess
import sys
import time
import warnings

import httpx
from langchain_core.tracers.context import collect_runs
from langchain_core.tracers.langchain import wait_for_all_tracers
from langsmith import Client
from langsmith.utils import LangSmithNotFoundError

from callguard_eval import CALLGUARD_DIR, callguard_version  # loads CallGuard's .env first

from callguard.answer import DEFAULT_MODEL, Answerer  # noqa: E402
from callguard.graph import CHECK_MODEL, CallFlow  # noqa: E402
from callguard.index import COLLECTION, EMBEDDING_MODEL, PROCESSED  # noqa: E402
from callguard.retrieve import Retriever  # noqa: E402

SAMPLE = "What is CVE-2024-41713, and are attackers using it?"  # exam question E1
PASS, FAIL = "✅", "❌"
results = []
shared = {}  # the local index can only be opened once per program, so the index and flow checks share it


def report(status, name, detail):
    results.append(status)
    print(f"{status} {name:<10} {detail}")


def check(name, fn):
    """Run one check, turning a crash into a red line instead of stopping the script."""
    try:
        fn()
    except Exception as e:
        report(FAIL, name, f"{type(e).__name__}: {e}")


def python():
    v = sys.version_info
    report(PASS if v[:2] == (3, 12) else FAIL, "Python", f"{v.major}.{v.minor}.{v.micro}")


def callguard():
    version = callguard_version()
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=CALLGUARD_DIR,
                            capture_output=True, text=True).stdout.strip()
    ok = not version.endswith("+changes")
    report(PASS if ok else FAIL, "CallGuard", f"{version} on branch {branch}, at {CALLGUARD_DIR}"
           + ("" if ok else " (unsaved changes: results couldn't be traced back to a version)"))


def keys():
    needed = ["NEBIUS_API_KEY", "LANGSMITH_API_KEY"]
    missing = [k for k in needed if not os.getenv(k)]
    if missing:
        report(FAIL, "Keys", f"missing from {CALLGUARD_DIR / '.env'}: {', '.join(missing)}")
    elif os.getenv("LANGSMITH_TRACING", "").lower() != "true":
        report(FAIL, "Keys", "set LANGSMITH_TRACING=true in CallGuard's .env")
    else:
        report(PASS, "Keys", f"{' and '.join(needed)} found in CallGuard's .env; "
                             f"tracing to project '{os.getenv('LANGSMITH_PROJECT')}'")


def nebius():
    base = (os.getenv("NEBIUS_BASE_URL") or "https://api.tokenfactory.nebius.com/v1/").rstrip("/")
    r = httpx.get(f"{base}/models", headers={"Authorization": f"Bearer {os.environ['NEBIUS_API_KEY']}"}, timeout=30)
    r.raise_for_status()
    available = {m["id"] for m in r.json()["data"]}
    wanted = {"writer": DEFAULT_MODEL, "checker": CHECK_MODEL, "embeddings": EMBEDDING_MODEL}
    missing = [f"{role} {model}" for role, model in wanted.items() if model not in available]
    report(FAIL if missing else PASS, "Nebius", f"missing: {', '.join(missing)}" if missing else
           f"key accepted; writer, checker and embedding models available ({len(available)} models)")


def langsmith():
    next(iter(Client().list_projects(limit=1)), None)  # raises if the key is rejected
    report(PASS, "LangSmith", "key accepted")


def data():
    records = [json.loads(line) for line in open(PROCESSED / "cves.jsonl")]
    manifest = json.loads((PROCESSED / "manifest.json").read_text())
    shared["records"] = {r["id"]: r for r in records}
    report(PASS, "Data", f"{len(records)} CVE records, as of {manifest['collected_at'][:16].replace('T', ' ')} UTC")


def index():
    retriever = shared["retriever"] = Retriever()
    points, _ = retriever.client.scroll(COLLECTION, limit=5000, with_payload=True)
    indexed = {p.payload["record"]["id"]: p.payload["record"] for p in points}
    records = shared["records"]
    missing, extra = records.keys() - indexed.keys(), indexed.keys() - records.keys()
    stale = [cve for cve in records.keys() & indexed.keys() if records[cve] != indexed[cve]]
    if missing or extra or stale:
        report(FAIL, "Index", f"{len(missing)} records not indexed, {len(extra)} extra entries, {len(stale)} out of "
                              "date: rebuild it in CallGuard with uv run scripts/build_index.py")
    else:
        report(PASS, "Index", f"{len(indexed)} entries, each identical to its record")


def trace_link(run_id):
    """The LangSmith page where the question can be replayed step by step."""
    wait_for_all_tracers()
    client = Client()
    with warnings.catch_warnings():  # read_run and get_run_url are deprecated but work until 2027-01-31
        warnings.simplefilter("ignore", DeprecationWarning)
        for _ in range(10):  # a fast answer can be looked up before LangSmith has finished saving it
            try:
                return client.get_run_url(run=client.read_run(run_id))
            except LangSmithNotFoundError:
                time.sleep(1)
    return "(not saved yet)"


def flow():
    flow = CallFlow(Answerer(retriever=shared["retriever"]))
    with collect_runs() as runs:
        state = flow.ask(SAMPLE)
    a = state["answer"]
    ok = a.kind == "answer" and "CVE-2024-41713" in a.cited and not a.unsupported
    report(PASS if ok else FAIL, "Call flow", f"E1 answered by the {state['route']} route in {a.seconds} s, "
                                              f"citing {', '.join(a.cited) or 'nothing'}")
    print(f"{'':13}replay in LangSmith: {trace_link(runs.traced_runs[0].id)}")


if __name__ == "__main__":
    print("CallGuard evaluation: setup check\n")
    for name, fn in [("Python", python), ("CallGuard", callguard), ("Keys", keys), ("Nebius", nebius),
                     ("LangSmith", langsmith), ("Data", data), ("Index", index), ("Call flow", flow)]:
        check(name, fn)
    print(f"\n{results.count(PASS)} passed, {results.count(FAIL)} failed")
    sys.exit(1 if FAIL in results else 0)
