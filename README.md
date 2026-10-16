# CausalLab

Fit an additive outcome model with a binary treatment coefficient, measured confounder adjustment and empirical treatment-overlap diagnostics.

**Version0.2.0: local CPU research workbench.** Import a CSV, map the relevant columns, run the real calculation and inspect plots, tables and method assumptions. Export a JSON result report or exact replayable input. No API key, GPU, paid service or external model call is required.

## Why use it

An analyst compares exposed and unexposed observational units while adjusting for measured baseline variables; they need a transparent estimate and an explicit account of what identification still assumes.

## Start

```sh
docker compose up --build
```

Open http://127.0.0.1:8000 and choose **Load synthetic example**. All bundled data are explicitly synthetic. Import your own UTF-8 CSV to use actual observations; their provenance remains unverified by the application.

Python3.12+ alternative:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install '.[dev]'
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API example:

```sh
curl --fail -H 'Content-Type: application/json' --data-binary @examples/synthetic.json http://127.0.0.1:8000/analyze
```

## Inputs, outputs and scientific scope

At least ten total rows and three rows in each treatment group. Treatment must be exactly0/1. At least one and at most50 numeric confounders are required. All rows align by CSV row; rectangular inputs and full-rank designs are required. Do not include post-treatment variables without a justified causal design.

Treatment coefficient is in outcome units for moving from treatment0 to1 in the fitted additive model. The interval uses a large-sample approximation, not a guarantee. Poor_overlap_fraction is the share of fitted propensity scores outside the extreme-score range; absence of warning is not proof of overlap or unconfoundedness.

Causal interpretation requires no unmeasured confounding, consistency, positivity and correct additive outcome specification. The tool cannot verify those assumptions, discover a causal graph, choose confounders, handle instruments or deliver individualized effects. Small samples may produce unreliable intervals.

Read the [complete user guide](docs/USER_GUIDE.md) for the walkthrough, methods, export/replay, data limits and troubleshooting. A CSV sample is in `examples/synthetic.csv`; the JSON example calls the same API.

## Validate

```sh
pip install '.[dev]'
pytest -q
node tools/test_ui.mjs
pip-audit --strict
bandit -r app -ll
```

Node is needed only for frontend development checks. Fresh rebuild evidence is in `evidence/rebuild/`. No Docker runtime, remote CI, publication or human review is implied merely by creating files. Required CI must pass before merging. Containers bind localhost and run nonroot; add authentication, HTTPS and deployment resource limits before external access. MIT license.
