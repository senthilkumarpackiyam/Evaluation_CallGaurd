"""CallGuard's LangSmith evaluation: the golden dataset, the evaluators and the runs."""

import subprocess
from pathlib import Path

import callguard

ROOT = Path(__file__).resolve().parents[2]
CALLGUARD_DIR = Path(callguard.__file__).resolve().parents[2]

callguard.load_settings()  # the keys come from CallGuard's own .env, so they live in one place only


def callguard_version():
    """Which CallGuard is being evaluated: its git tag or commit, plus "+changes" if it has unsaved edits.
    Every LangSmith experiment records this, so a result can always be traced back to the code that produced it."""
    def git(*args):
        return subprocess.run(["git", *args], cwd=CALLGUARD_DIR, capture_output=True, text=True).stdout.strip()
    dirty = bool(git("status", "--porcelain", "--untracked-files=no"))
    return git("describe", "--tags", "--always") + ("+changes" if dirty else "")
