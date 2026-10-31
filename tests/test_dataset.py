"""The golden dataset is valid, and the checker catches the mistakes it is meant to catch."""

import copy

import pytest

from callguard_eval.dataset import example_id, load_cases, load_records, problems, to_example


@pytest.fixture(scope="module")
def cases():
    return load_cases()


@pytest.fixture(scope="module")
def records():
    return load_records()


def broken(cases, case_id, **changes):
    changed = copy.deepcopy(cases)
    case = next(c for c in changed if c["id"] == case_id)
    for key, value in changes.items():
        if value is None:
            case.pop(key, None)
        else:
            case[key] = value
    return changed


def test_the_dataset_has_no_problems(cases, records):
    assert problems(cases, records) == []


def test_a_cve_missing_from_the_data_is_caught(cases, records):
    assert any("CVE-2099-0001 is not in the data" in p
               for p in problems(broken(cases, "E1", cves=["CVE-2099-0001"]), records))


def test_a_made_up_cve_in_a_reference_is_caught(cases, records):
    assert any("mentions CVE-2099-0001" in p
               for p in problems(broken(cases, "E1", answer="Chained with CVE-2099-0001."), records))


def test_the_group_mix_is_enforced(cases, records):
    assert any("happy-path: 19 cases" in p for p in problems(broken(cases, "E1", group="edge"), records))


def test_a_refusal_needs_a_reason(cases, records):
    assert any("needs a reason" in p for p in problems(broken(cases, "R2", reason=None), records))


def test_refusal_reasons_follow_callguards_product_list(cases, records):
    assert any("not cloud" in p
               for p in problems(broken(cases, "R2", question="Is Mitel MiCollab affected?"), records))


def test_freshness_answers_follow_the_data(cases, records):
    assert any(p.startswith("F2:") for p in problems(broken(cases, "F2", cves=["CVE-2024-41713"]), records))


def test_example_ids_are_stable_and_unique(cases):
    ids = [example_id(c["id"]) for c in cases]
    assert len(set(ids)) == len(cases)
    assert example_id("E1") == example_id("E1")


def test_the_malformed_input_survives_loading(cases):
    question = to_example(next(c for c in cases if c["id"] == "A2"))["inputs"]["question"]
    assert "\x1b[2J" in question and "‮" in question and "<script>" in question
    assert "\x00" not in question  # LangSmith (Postgres) can't store a NUL byte, so the case spells it out instead
