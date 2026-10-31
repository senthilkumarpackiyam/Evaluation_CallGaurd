"""The golden dataset: the 40 cases in dataset/golden.toml, how they are checked, and how they become LangSmith
examples (the question goes in; the expectations are the reference outputs the evaluators compare against)."""

import json
import re
import tomllib
import uuid
from datetime import date, timedelta

from callguard_eval import ROOT

from callguard.index import PROCESSED  # noqa: E402
from callguard.products import load_products  # noqa: E402
from callguard.understand import understand  # noqa: E402

DATASET_FILE = ROOT / "dataset" / "golden.toml"
EXAMPLES_FILE = ROOT / "dataset" / "golden.jsonl"
DATASET_NAME = "callguard-golden-40"
GROUPS = {"happy-path": 20, "edge": 12, "known-failure": 6, "adversarial": 2}  # the mix the brief asks for
TYPES = {"exact-id", "version", "meaning", "multi-step", "freshness", "refuse", "list-all", "adversarial"}
EXPECTS = {"answer", "refuse", "resist"}
REASONS = {"unknown product", "unknown cve", "cloud", "out of scope", "internal data", "no records"}
REQUIRED = ["id", "group", "type", "source", "question", "expect", "cves", "answer", "tests"]
CVE_ID = re.compile(r"CVE-\d{4}-\d{4,}")
CISCO_CONTACT_CENTER = {"C4", "C6", "C7", "C8", "C9"}  # UCCX, UCCE/PCCE, Finesse, CVP, CUIC (as in CallGuard's exam)


def load_cases():
    return tomllib.loads(DATASET_FILE.read_text())["case"]


def load_records():
    return {r["id"]: r for r in (json.loads(line) for line in open(PROCESSED / "cves.jsonl"))}


def example_id(case_id):
    """A fixed ID for each case, so uploading again updates the same LangSmith example instead of adding a copy."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://github.com/senthilkumarpackiyam/Evaluation_CallGaurd/{case_id}"))


def to_example(case):
    return {
        "id": example_id(case["id"]),
        "inputs": {"question": case["question"]},
        "outputs": {"expect": case["expect"], "reason": case.get("reason"), "cves": case["cves"],
                    "answer": case["answer"], "must_not": case.get("must_not", [])},
        "metadata": {"case_id": case["id"], "group": case["group"], "type": case["type"], "source": case["source"],
                     "tests": case["tests"], **({"known_issue": case["known_issue"]} if "known_issue" in case else {})},
        "split": case["group"],
    }


def freshness_expectations(records):
    """F1 and F2 depend on the data's date. The data is frozen, so they are written down in the dataset; this
    works them out again from the records, the way CallGuard's exam did, to prove the written answers still hold."""
    manifest = json.loads((PROCESSED / "manifest.json").read_text())
    as_of = date.fromisoformat(manifest["collected_at"][:10])
    in_scope = [r for r in records.values() if any(p["scope"] == "in" for p in r["products"])]
    since = (as_of - timedelta(days=7)).isoformat()
    newest = max(in_scope, key=lambda r: r["published"])
    newest_cisco = max((r for r in in_scope if {p["id"] for p in r["products"]} & CISCO_CONTACT_CENTER),
                       key=lambda r: r["published"])
    return {"as_of": as_of.isoformat(),
            "F1": {"cves": sorted(r["id"] for r in in_scope if r["published"] >= since), "newest": newest["id"]},
            "F2": {"cves": [newest_cisco["id"]], "published": newest_cisco["published"]}}


def problems(cases, records):
    """Everything wrong with the dataset, as a list of sentences (empty when it is ready to upload)."""
    found = []
    ids = [c.get("id") for c in cases]
    found += [f"{i}: the ID is used more than once" for i in sorted({i for i in ids if ids.count(i) > 1})]
    counts = {g: sum(c.get("group") == g for c in cases) for g in GROUPS}
    found += [f"group {g}: {counts[g]} cases, the brief asks for {n}" for g, n in GROUPS.items() if counts[g] != n]
    found += [f"{c.get('id')}: unknown group {c.get('group')!r}" for c in cases if c.get("group") not in GROUPS]
    products = load_products()
    for c in cases:
        cid = c.get("id")
        found += [f"{cid}: missing {field}" for field in REQUIRED if field not in c]
        if c.get("type") not in TYPES:
            found.append(f"{cid}: unknown type {c.get('type')!r}")
        if c.get("source") not in ("exam", "new"):
            found.append(f"{cid}: source must be 'exam' or 'new'")
        if c.get("expect") not in EXPECTS:
            found.append(f"{cid}: expect must be one of {sorted(EXPECTS)}")
        if c.get("expect") == "refuse":
            if c.get("reason") not in REASONS:
                found.append(f"{cid}: a refusal needs a reason from {sorted(REASONS)}")
            if c.get("cves"):
                found.append(f"{cid}: a refusal should expect no CVEs")
        elif "reason" in c:
            found.append(f"{cid}: only refusals have a reason")
        if (c.get("group") == "known-failure") != ("known_issue" in c):
            found.append(f"{cid}: known-failure cases, and only those, describe their known_issue")
        for cve in c.get("cves", []):
            if cve not in records:
                found.append(f"{cid}: expected {cve} is not in the data")
            elif not any(p["scope"] == "in" for p in records[cve]["products"]):
                found.append(f"{cid}: expected {cve} is not for a product CallGuard covers")
        # Every CVE the reference mentions must be real, except the deliberately unknown one in an "unknown cve" case
        for cve in set(CVE_ID.findall(c.get("answer", ""))) - records.keys():
            if c.get("reason") != "unknown cve":
                found.append(f"{cid}: the reference mentions {cve}, which is not in the data")
        # The refusal reasons that depend on the product list must agree with CallGuard's product list
        if c.get("reason") in ("cloud", "out of scope", "unknown product"):
            scopes = {p.scope for p in understand(c["question"], products).products}
            wanted = {"cloud": {"cloud"}, "out of scope": {"out"}, "unknown product": set()}[c["reason"]]
            if scopes != wanted:
                found.append(f"{cid}: CallGuard's product list gives scopes {scopes or 'none'}, not {c['reason']}")
    fresh = freshness_expectations(records)
    by_id = {c.get("id"): c for c in cases}
    if "F1" in by_id and (by_id["F1"]["cves"] != fresh["F1"]["cves"] or fresh["F1"]["newest"] not in by_id["F1"]["answer"]
                          or fresh["as_of"] not in by_id["F1"]["answer"]):
        found.append(f"F1: the data says {fresh['F1']} as of {fresh['as_of']}")
    if "F2" in by_id and (by_id["F2"]["cves"] != fresh["F2"]["cves"]
                          or fresh["F2"]["published"] not in by_id["F2"]["answer"]):
        found.append(f"F2: the data says {fresh['F2']}")
    return found
