# CausalLab

Fit an additive outcome model with a binary treatment coefficient, measured confounder adjustment and empirical treatment-overlap diagnostics.

**Version 0.3.0: local CPU research workbench.** Import a CSV, map the relevant columns, run the real calculation and inspect plots, tables and method assumptions. Export a JSON result report or exact replayable input. No API key, GPU, paid service or external model call is required.

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

Node is needed only for frontend development checks. Fresh v0.3.0 developer evidence is in `evidence/improvements-0.3/`; previous v0.2 records remain historical. No Docker runtime, remote CI, publication or human review is implied merely by creating files. Required CI must pass before merging. Containers bind localhost and run nonroot; add authentication, HTTPS and deployment resource limits before external access. MIT license.

## v0.3.0: descriptive covariate balance

The UI now reports raw treated/control counts and a balance table for every selected confounder. CSV column labels are sent as optional `confounder_names`; API clients can omit names for backward-compatible `confounder_0`, etc. Supplied names must match matrix width, be nonempty and unique after trimming, and each contain at most100 characters.

`covariate_balance` contains control/treated means, pooled sample SD, signed treated-minus-control SMD, absolute SMD, a descriptive flag, and a zero-variance indicator. For group sizes n0/n1 and **sample** variances s0²/s1², pooled SD = sqrt(((n0−1)s0²+(n1−1)s1²)/(n0+n1−2)). SMD = (treated mean−control mean)/pooled SD. Example: groups[1,2,3,4,5] and[2,3,4,5,6] have means3/4, pooled SDsqrt(2.5) and SMD≈0.63246.

The |SMD|≥0.1 flag is a descriptive heuristic, not a test, p-value, causal criterion or evidence that an intervention should proceed. Diagnostics describe **raw unweighted groups before adjustment**; OLS does not make these groups balanced. A low SMD cannot prove no hidden confounding, positivity, or correct functional form. Zero pooled variance with unequal means yields null SMD and a flag; identical constant groups yield SMD0. The existing full-rank outcome-model requirement still rejects constant/collinear input designs. HC1 standard errors and normal-approximation intervals are unchanged. Exported reports include group counts and the full balance table.
