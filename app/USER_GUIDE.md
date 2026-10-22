# CausalLab user guide — v0.4.0

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

OLS fits outcome = intercept + treatment coefficient × binary treatment + confounder coefficients. HC1 heteroskedasticity-robust covariance supplies a normal-approximation interval. By default, a regularized logistic fit on standardized confounders supplies overlap diagnostics only, flagging empirical extreme propensities (below 0.05 or above 0.95); this default path does not estimate a second effect or establish positivity. When optional IPW is enabled, those fitted propensities also produce the separate clipped Hájek ATE estimate described below. Neither use establishes population positivity or controls unmeasured confounding.

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

Python tests exercise numerical results and actual HTTP endpoints. Node tests exercise CSV parsing, column mapping, numeric rejection and the synthetic analysis payload. Node22+ is used for development checks; it is not a runtime service dependency. Fresh v0.4.0 developer evidence is under `evidence/improvements-0.4/`; it records what was run and does not establish unexecuted Docker, GitHub CI or human validation. Configure required CI checks and never merge a failing release.

MIT license; see LICENSE.

## v0.4.0: descriptive covariate balance

The UI now reports raw treated/control counts and a balance table for every selected confounder. CSV column labels are sent as optional `confounder_names`; API clients can omit names for backward-compatible `confounder_0`, etc. Supplied names must match matrix width, be nonempty and unique after trimming, and each contain at most100 characters.

`covariate_balance` contains control/treated means, pooled sample SD, signed treated-minus-control SMD, absolute SMD, a descriptive flag, and a zero-variance indicator. For group sizes n0/n1 and **sample** variances s0²/s1², pooled SD = sqrt(((n0−1)s0²+(n1−1)s1²)/(n0+n1−2)). SMD = (treated mean−control mean)/pooled SD. Example: groups[1,2,3,4,5] and[2,3,4,5,6] have means3/4, pooled SDsqrt(2.5) and SMD≈0.63246.

The |SMD|≥0.1 flag is a descriptive heuristic, not a test, p-value, causal criterion or evidence that an intervention should proceed. Diagnostics describe **raw unweighted groups before adjustment**; OLS does not make these groups balanced. A low SMD cannot prove no hidden confounding, positivity, or correct functional form. Zero pooled variance with unequal means yields null SMD and a flag; identical constant groups yield SMD0. The existing full-rank outcome-model requirement still rejects constant/collinear input designs. HC1 standard errors and normal-approximation intervals are unchanged. Exported reports include group counts and the full balance table.

## v0.4.0: optional Hájek IPW comparison

Check **Also estimate Hájek IPW ATE** and choose a clipping bound; or add `include_ipw:true` and `propensity_clip:0.02` to `/analyze`. Default false preserves the OLS-only response. Existing OLS coefficients, HC1 standard errors and normal intervals remain. The added `ipw` result is a separate estimator with **no confidence interval**.

The existing L2-regularized logistic propensity model is fitted to standardized measured confounders. A checked-convergence, adequately conditioned fit is required. Probabilities are clipped to[clip,1−clip], clip0.001–0.2. Treated weights are1/p; control weights are1/(1−p). Each arm's weighted outcome mean is normalized by that arm's sum of weights; their difference is the Hájek ATE. ESS per group is(sum w)²/sum(w²). Outputs include clipping count/fraction and a warning whenever clipping occurred. Clipping can reduce extreme weights but introduce bias; estimates need not agree with OLS.

Weighted covariate means are compared using the **same raw pooled sample SD** as the raw SMD, allowing a descriptive before/after weighting comparison. Balance/ESS do not establish causal identification. IPW requires correct propensity specification, positivity, consistency and no unmeasured confounding. No cross-fitting, doubly robust estimation, longitudinal exposure model or uncertainty quantification is provided. At most5,000 rows/20 confounders are permitted for IPW; the same full-rank OLS input requirements still apply because both estimates are returned. Nonconverged/poorly conditioned propensity fits are rejected rather than reported as certain estimates.

Synthetic complete request: `examples/synthetic-ipw.json`. Background: [Cole and Hernán2008, inverse-probability weight construction](https://pubmed.ncbi.nlm.nih.gov/18682488/); this tool implements a bounded single-time binary-treatment Hájek estimator, not every method discussed in that paper.
