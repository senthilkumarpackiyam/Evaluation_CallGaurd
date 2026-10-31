# Evaluating CallGuard with LangSmith

[CallGuard](https://github.com/senthilkumarpackiyam/callguard) answers "are we exposed?" questions about known vulnerabilities in contact-center and unified-communications products, from NVD, CISA KEV and FIRST EPSS data. This repository evaluates it the way a QA team would:

1. a **40-case golden dataset**: 20 happy-path, 12 edge, 6 known-failure and 2 adversarial cases
2. a **LangSmith dataset** run with `client.evaluate()`, scored by code evaluators and an LLM judge
3. a **baseline run**, failures **clustered** by cause, **3–4 fixes**, and a **re-run** with the changes measured

> Work in progress. The plan is in [ROADMAP.md](ROADMAP.md) and the status in [docs/PROGRESS.md](docs/PROGRESS.md).

## Set up

You need macOS or Linux, [uv](https://docs.astral.sh/uv/), a [Nebius Token Factory](https://tokenfactory.nebius.com) key and a [LangSmith](https://smith.langchain.com) key.

CallGuard must sit next to this folder, as `CallGaurd`, on its `evaluation` branch, with its search index built:

```bash
git clone -b evaluation https://github.com/senthilkumarpackiyam/callguard.git CallGaurd
git clone https://github.com/senthilkumarpackiyam/Evaluation_CallGaurd.git
(cd CallGaurd && cp .env.example .env)   # add your Nebius and LangSmith keys to CallGaurd/.env
(cd CallGaurd && uv sync && uv run scripts/build_index.py)
cd Evaluation_CallGaurd
uv sync
uv run scripts/check_setup.py            # Python, CallGuard, keys, models, data, index and one question
```

The keys stay in CallGuard's `.env`. This project reads them from there and never prints them.

## The golden dataset

All 40 cases are listed in [`dataset/README.md`](dataset/README.md). The source is [`dataset/golden.toml`](dataset/golden.toml): 25 questions from CallGuard's exam, which was written before CallGuard was built, plus 15 new ones.

| Group | Cases | What's in it |
|---|---|---|
| Happy path | 20 | Lookups by CVE number, version checks, plain-language searches, patch priorities and freshness, across Cisco, Avaya, Mitel, Asterisk, FreePBX, Genesys and Verint |
| Edge | 12 | Version boundaries, an empty time window, a misspelled product, a "v" version prefix, a mistyped CVE number, two CVEs at once, a lower-case CVE ID, and five questions that must be declined |
| Known failure | 6 | The weaknesses in CallGuard's own failure analysis, plus a "list every…" question with more answers than one search returns |
| Adversarial | 2 | A prompt injection asking for a false "safe", and 771 characters of malformed input around one real question |

```bash
uv run scripts/check_dataset.py    # checks all 40 against CallGuard's data
uv run scripts/upload_dataset.py   # uploads them to LangSmith as callguard-golden-40 (safe to repeat)
uv run pytest                      # tests, including that the checker catches broken cases
```
