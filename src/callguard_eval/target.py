"""The system under test: CallGuard's full call flow. One question goes in; out comes the answer plus everything the
evaluators need (route, records retrieved, citations, time, and exactly what the writer model was shown)."""

import json

from callguard_eval import callguard_version  # loads CallGuard's .env first

from callguard.answer import DEFAULT_MODEL, Answerer  # noqa: E402
from callguard.graph import CHECK_MODEL, SEARCH_K, CallFlow  # noqa: E402
from callguard.index import PROCESSED  # noqa: E402
from callguard.retrieve import Retriever  # noqa: E402


class PromptRecorder:
    """Keeps a copy of the last prompt sent to the writer model. CallGuard itself is unchanged; only the evaluation
    reads the copy. The faithfulness judge must see exactly what the writer saw, including the facts code worked out
    (version checks, patch order, "nothing published in the past 7 days"), not just the records, or it would mark
    those facts as unsupported."""

    def __init__(self, answerer):
        self.last = None
        completions = answerer.llm.chat.completions
        create = completions.create

        def recording_create(*args, **kwargs):
            self.last = kwargs.get("messages")
            return create(*args, **kwargs)

        completions.create = recording_create


def writer_prompt(messages):
    """Both parts of what the writer saw: its instructions (which list the products CallGuard covers) and its input
    (the question, the facts code worked out, and the records)."""
    if not messages:
        return None
    parts = {}
    for m in messages:  # the first of each: after a citation-guard rewrite, the last "user" message is the correction
        parts.setdefault(m["role"], m["content"])
    return f"THE WRITER'S INSTRUCTIONS:\n{parts.get('system', '')}\n\nTHE WRITER'S INPUT:\n{parts.get('user', '')}"


def describe():
    """What is being evaluated, for the experiment's metadata."""
    manifest = json.loads((PROCESSED / "manifest.json").read_text())
    return {"callguard": callguard_version(), "writer": DEFAULT_MODEL, "checker": CHECK_MODEL,
            "records_per_search": SEARCH_K, "data_as_of": manifest["collected_at"]}


def make_target():
    flow = CallFlow(Answerer(retriever=Retriever()))
    recorder = PromptRecorder(flow.answerer)

    def callguard(inputs):
        recorder.last = None
        try:
            state = flow.ask(inputs["question"])
        except Exception as e:  # an input that crashes CallGuard is a result to score, not a reason to stop the run
            return {"kind": "error", "error": f"{type(e).__name__}: {e}"}
        a = state["answer"]
        return {"answer": a.body, "text": a.text, "kind": a.kind, "refusal_reason": a.reason,
                "route": state["route"], "rephrased": state.get("rephrased", 0),
                "check": (state.get("check") or {}).get("why"),
                "retrieved": a.retrieved or [h.record["id"] for h in state.get("hits", [])],
                "cited": a.cited, "unsupported": a.unsupported, "seconds": a.seconds, "tokens": a.tokens,
                "rewritten": getattr(a, "rewritten", 0),  # the citation guard (CallGuard v1.2 and later)
                "writer_prompt": writer_prompt(recorder.last)}

    return callguard
