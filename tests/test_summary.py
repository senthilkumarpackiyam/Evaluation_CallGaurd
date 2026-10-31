"""Averages count only the runs a measure applies to, and failures are found per run."""

from callguard_eval.summary import averages, cases, noise, run_failures


def run(case_id, rep, seconds, **scores):
    return {"case_id": case_id, "group": "edge", "type": "refuse", "repetition": rep, "url": f"u/{case_id}/{rep}",
            "outputs": {"kind": "answer", "route": "search", "seconds": seconds}, "scores": scores,
            "comments": {k: f"why {k}" for k in scores}}


ROWS = [run("R1", 1, 2.0, refusal_correct=1, correctness=1.0),
        run("R1", 2, 3.0, refusal_correct=0, correctness=0.5),
        run("E1", 1, 4.0, cves_found=1.0, correctness=1.0),
        run("E1", 2, 5.0, cves_found=0.5, correctness=1.0)]


def test_a_measure_is_averaged_only_where_it_applies():
    overall = averages(ROWS)
    assert overall["refusal_correct"] == 0.5   # the two refusal runs, not all four
    assert overall["cves_found"] == 0.75       # the two lookup runs
    assert overall["correctness"] == 0.875
    assert overall["p50"] == 3.5


def test_noise_is_the_spread_between_repetitions():
    assert noise(ROWS)["correctness"] == (0.75, 1.0)


def test_failures_are_found_per_run_with_their_explanation():
    assert run_failures(ROWS[1]) == [("correctness", "why correctness"), ("refusal_correct", "why refusal_correct")]
    by_case = {c["case_id"]: c for c in cases(ROWS)}
    assert by_case["R1"]["failed_runs"] == 1 and by_case["E1"]["failures"] == {"cves_found": ["why cves_found"]}
