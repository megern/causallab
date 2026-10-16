# CausalLab user guide — v0.2.0

## What this tool does

Fit an additive outcome model with a binary treatment coefficient, measured confounder adjustment and empirical treatment-overlap diagnostics.

Use case: An analyst compares exposed and unexposed observational units while adjusting for measured baseline variables; they need a transparent estimate and an explicit account of what identification still assumes.

## Quickstart

Requires Docker Compose, or Python3.12+ for the installed pinned NumPy dependency. No API key, remote model, GPU or paid service is used.

```sh
docker compose up --build
```

Open http://127.0.0.1:8000. The interactive workbench loads a clearly labeled synthetic example. API docs: http://127.0.0.1:8000/docs. Change the host port in compose if running several tools together.

Without Docker:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install '.[dev]'
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Walkthrough

1. Load the synthetic 80-row example. Map `outcome` and `treatment`.
2. Select `baseline` and `experience` as confounders. Do not select treatment/outcome as confounders.
3. Estimate the adjusted effect. The example is constructed with a treatment coefficient near3; its artificial construction is not evidence about real organizations or interventions.
4. Inspect the coefficient, HC1 standard error, approximate interval, propensity range and warning.
5. Export the result and selected input. Record your actual assumptions and measurement provenance separately.

## Import and mapping

Import UTF-8 CSV with unique, nonempty header names. A BOM, CRLF, quoted commas, doubled quote escapes and quoted multiline fields are supported. Every data row must contain the same number of fields. Blank physical lines are ignored; empty fields within rows are not silently removed. The preview displays the first eight rows, while analysis uses all imported rows. Use mapping controls to select numeric columns; extra columns can remain unused. Import provenance is displayed as unverified, and imported values render as text.

Files and API requests are bounded at2MiB. CSV permits up to100 columns and100,000 rows; selected numeric matrices permit at most50 columns. Numbers must be finite with magnitude at most1e100. Imported files are read locally by the browser; selected data are sent to the local FastAPI service. The service holds requests in memory and does not persist them. No external network request is required by the workbench.

CSV format illustration (this fragment may be below the minimum sample size):

```csv
outcome,treatment,baseline,experience
2,0,0,0
6.8,1,2,0
4.4,0,3,0
```

Input requirements: At least ten total rows and three rows in each treatment group. Treatment must be exactly0/1. At least one and at most50 numeric confounders are required. All rows align by CSV row; rectangular inputs and full-rank designs are required. Do not include post-treatment variables without a justified causal design.

## Methods

OLS fits outcome = intercept + treatment coefficient × binary treatment + confounder coefficients. HC1 heteroskedasticity-robust covariance supplies a normal-approximation interval. A regularized logistic fit on standardized confounders diagnoses empirical extreme propensities (below0.05 or above0.95); it does not estimate a second effect or establish positivity.

## Read the output

Treatment coefficient is in outcome units for moving from treatment0 to1 in the fitted additive model. The interval uses a large-sample approximation, not a guarantee. Poor_overlap_fraction is the share of fitted propensity scores outside the extreme-score range; absence of warning is not proof of overlap or unconfoundedness.

The workbench provides metric cards, a plot, interpretation and exact result table. For long time sequences, the table shows the first300 rows; the API report includes the complete arrays. Charts summarize calculations, not additional fitted models. The expandable API response exposes exact values. Change any mapping or parameter to clear old results, then rerun; an in-flight result is discarded if settings changed.

## Export and replay

**Export result report (JSON)** downloads application/version, timestamp, provenance label, mapping/settings and computed result. **Export replayable input (JSON)** includes selected numeric data and is exactly the `/analyze` request format. Exports are local downloads; review them for sensitive data before sharing. There is no result CSV export and therefore no spreadsheet-formula export interpretation. Synthetic example CSV uses only fixed headers/numeric values.

```sh
curl --fail -H 'Content-Type: application/json' --data-binary @examples/synthetic.json http://127.0.0.1:8000/analyze
curl --fail -H 'Content-Type: application/json' --data-binary @downloaded-analysis-input.json http://127.0.0.1:8000/analyze
```

See examples/synthetic.json for a valid complete effect-estimation request; a short CSV fragment is not a valid full sample.

## Assumptions and limits

Causal interpretation requires no unmeasured confounding, consistency, positivity and correct additive outcome specification. The tool cannot verify those assumptions, discover a causal graph, choose confounders, handle instruments or deliver individualized effects. Small samples may produce unreliable intervals.

These are bounded local research tools. Synthetic fixtures do not establish external scientific validity. No domain expert or human audit is claimed. For network exposure, configure authentication, HTTPS, rate limits and deployment concurrency/memory bounds. Defaults bind to localhost and containers run without root privileges.

## Troubleshooting

Collinear design: remove duplicate/constant confounders or a column equal to treatment; collect more independent observations. Missing treatment group: include genuine controls and treated units. Overlap warning: inspect the assignment process and consider a justified target population; do not mechanically delete rows to force a warning away.

CSV row/column error: fix the named row; do not convert a missing observation to zero automatically. HTTP422: inspect the specific schema/algorithm message and adjust mapping or input. HTTP413: reduce selected rows/columns below the2MiB request bound. File parse errors clear the usable dataset and results. For a browser error, inspect local service availability; restart only after reviewing the service log. If a download fails, check browser download permissions.

## Reproducibility and checks

```sh
pytest -q
node tools/test_ui.mjs
pip-audit --strict
bandit -r app -ll
```

Python tests exercise numerical results and actual HTTP endpoints. Node tests exercise CSV parsing, column mapping, numeric rejection and the synthetic analysis payload. Node22+ is used for development checks; it is not a runtime service dependency. Fresh rebuild evidence is under `evidence/rebuild/`; it records what was run and does not establish unexecuted Docker, GitHub CI or human validation. Configure required CI checks and never merge a failing release.

MIT license; see LICENSE.
