from .access import AccessControl
import math
from .guard import InputGuard
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel, Field, model_validator


def finite(values):
    if not all(abs(v) <= 1e100 and math.isfinite(v) for v in values):
        raise ValueError("numeric values must be finite with magnitude at most 1e100")


def matrix(rows):
    if (
        not rows
        or not rows[0]
        or len(rows[0]) > 50
        or any(len(row) != len(rows[0]) for row in rows)
    ):
        raise ValueError("numeric matrix must be rectangular with 1 to 50 columns")
    finite([v for row in rows for v in row])


class Request(BaseModel):
    outcome: list[float] = Field(min_length=10, max_length=100000)
    treatment: list[int] = Field(min_length=10, max_length=100000)
    confounders: list[list[float]] = Field(min_length=10, max_length=100000)

    confounder_names: list[str] | None = Field(default=None, max_length=50)

    include_ipw: bool = False
    propensity_clip: float = Field(default=0.02, ge=0.001, le=0.2, allow_inf_nan=False)

    @model_validator(mode="after")
    def valid(self):
        matrix(self.confounders)
        if self.include_ipw and (
            len(self.outcome) > 5000 or len(self.confounders[0]) > 20
        ):
            raise ValueError("IPW is bounded to 5000 rows and 20 confounders")
        finite(self.outcome)
        if len(self.outcome) != len(self.treatment) or len(self.outcome) != len(
            self.confounders
        ):
            raise ValueError("row counts must match")
        if (
            set(self.treatment) != {0, 1}
            or min(self.treatment.count(0), self.treatment.count(1)) < 3
        ):
            raise ValueError(
                "binary treatment needs at least three observations in each group"
            )
        if self.confounder_names is not None and (
            len(self.confounder_names) != len(self.confounders[0])
            or any(
                not name.strip() or len(name) > 100 for name in self.confounder_names
            )
            or len(set(name.strip() for name in self.confounder_names))
            != len(self.confounder_names)
        ):
            raise ValueError(
                "confounder_names must be nonempty, unique after trimming, at most 100 characters, and match column count"
            )
        return self


def covariate_balance(confounders, treatment, names):
    """Descriptive, unweighted raw-group balance; no adjustment or causal test."""
    control, treated = confounders[treatment == 0], confounders[treatment == 1]
    n0, n1 = len(control), len(treated)
    diagnostics = []
    for index, name in enumerate(names):
        mean0, mean1 = float(control[:, index].mean()), float(treated[:, index].mean())
        variance0, variance1 = (
            float(control[:, index].var(ddof=1)),
            float(treated[:, index].var(ddof=1)),
        )
        pooled_sd = math.sqrt(
            ((n0 - 1) * variance0 + (n1 - 1) * variance1) / (n0 + n1 - 2)
        )
        difference = mean1 - mean0
        smd = (
            difference / pooled_sd
            if pooled_sd > 0
            else (0.0 if difference == 0 else None)
        )
        diagnostics.append(
            {
                "confounder": name,
                "control_mean": mean0,
                "treated_mean": mean1,
                "pooled_sample_sd": pooled_sd,
                "standardized_mean_difference": smd,
                "absolute_smd": abs(smd) if smd is not None else None,
                "descriptive_imbalance_flag": (
                    abs(smd) >= 0.1 if smd is not None else True
                ),
                "zero_pooled_variance": pooled_sd == 0,
            }
        )
    return diagnostics


def analyze(req: Request):
    y, t, c = (
        np.asarray(req.outcome),
        np.asarray(req.treatment),
        np.asarray(req.confounders),
    )
    x = np.column_stack([np.ones(len(y)), t, c])
    if len(y) <= x.shape[1] or np.linalg.matrix_rank(x) != x.shape[1]:
        raise ValueError("insufficient observations or collinear treatment/confounders")
    coefficients = np.linalg.lstsq(x, y, rcond=None)[0]
    residual = y - x @ coefficients
    bread = np.linalg.inv(x.T @ x)
    meat = x.T @ (x * residual[:, None] ** 2)
    covariance = bread @ meat @ bread * len(y) / (len(y) - x.shape[1])
    if not np.all(np.isfinite(covariance)):
        raise ValueError("robust covariance overflow; rescale numeric inputs")
    se = float(np.sqrt(max(0, covariance[1, 1])))
    # A regularized logistic fit diagnoses empirical overlap; it does not establish identification.
    z = np.column_stack(
        [np.ones(len(y)), (c - c.mean(0)) / np.where(c.std(0) > 1e-12, c.std(0), 1)]
    )
    if req.include_ipw and np.linalg.cond(z) > 1e10:
        raise ValueError(
            "IPW propensity design is poorly conditioned; remove redundant columns"
        )
    converged = False
    beta = np.zeros(z.shape[1])
    for _ in range(100):
        p = 1 / (1 + np.exp(-np.clip(z @ beta, -30, 30)))
        w = np.maximum(p * (1 - p), 1e-8)
        ridge = np.diag(np.r_[1e-8, np.ones(z.shape[1] - 1) * 0.01])
        step = np.linalg.solve(
            z.T @ (z * w[:, None]) + ridge, z.T @ (t - p) - ridge @ beta
        )
        beta += step
        if np.linalg.norm(step) < 1e-8:
            converged = True
            break
    p = 1 / (1 + np.exp(-np.clip(z @ beta, -30, 30)))
    fraction = float(np.mean((p < 0.05) | (p > 0.95)))
    names = (
        [name.strip() for name in req.confounder_names]
        if req.confounder_names is not None
        else [f"confounder_{i}" for i in range(c.shape[1])]
    )
    optional = {}
    if req.include_ipw:
        if not converged:
            raise ValueError(
                "propensity solver did not converge; no IPW estimate reported"
            )
        clipped = np.clip(p, req.propensity_clip, 1 - req.propensity_clip)
        weights = np.where(t == 1, 1 / clipped, 1 / (1 - clipped))
        means = [
            float(np.average(y[t == group], weights=weights[t == group]))
            for group in [0, 1]
        ]
        raw = covariate_balance(c, t, names)
        weighted = []
        for i, item in enumerate(raw):
            m0 = float(np.average(c[t == 0, i], weights=weights[t == 0]))
            m1 = float(np.average(c[t == 1, i], weights=weights[t == 1]))
            sd = item["pooled_sample_sd"]
            weighted.append(
                {
                    "confounder": names[i],
                    "control_weighted_mean": m0,
                    "treated_weighted_mean": m1,
                    "raw_smd": item["standardized_mean_difference"],
                    "weighted_smd": (
                        (m1 - m0) / sd if sd > 0 else (0.0 if m1 == m0 else None)
                    ),
                }
            )
        count = int(np.sum(p != clipped))
        optional["ipw"] = {
            "estimator": "Hajek normalized inverse-probability weighted ATE",
            "ate": means[1] - means[0],
            "control_weighted_outcome": means[0],
            "treated_weighted_outcome": means[1],
            "group_counts": {
                "control": int(np.sum(t == 0)),
                "treated": int(np.sum(t == 1)),
            },
            "effective_sample_size": {
                label: float(
                    weights[t == group].sum() ** 2 / np.sum(weights[t == group] ** 2)
                )
                for group, label in [(0, "control"), (1, "treated")]
            },
            "propensity_clip": req.propensity_clip,
            "clipped_observations": count,
            "clipped_fraction": count / len(t),
            "weighted_balance": weighted,
            "confidence_interval": None,
            "warnings": (
                [
                    "Propensities clipped: clipping changes weights and can introduce bias."
                ]
                if count
                else []
            ),
            "limitations": "Uses the existing regularized logistic propensity model fitted on observed confounders. Weighted SMD uses raw pooled sample SD as a fixed descriptive denominator. No cross-fitting, doubly robust correction or uncertainty interval. Requires consistency, positivity and no unmeasured confounding; fitted balance/ESS do not prove identification.",
        }
    return {
        **optional,
        "group_counts": {
            "control": int(np.sum(t == 0)),
            "treated": int(np.sum(t == 1)),
        },
        "covariate_balance": covariate_balance(c, t, names),
        "balance_method": "Raw, unweighted treated-minus-control mean divided by pooled sample SD: sqrt(((n0-1)*s0^2+(n1-1)*s1^2)/(n0+n1-2)). Absolute SMD >= 0.1 is a descriptive heuristic only; low SMD does not prove positivity, unconfoundedness, or causal identification. These are pre-adjustment groups, not a claim that OLS balanced covariates. Zero pooled SD with unequal means yields null SMD and a warning flag.",
        "treatment_effect": float(coefficients[1]),
        "robust_standard_error": se,
        "approximate_95_percent_interval": [
            float(coefficients[1] - 1.96 * se),
            float(coefficients[1] + 1.96 * se),
        ],
        "propensity_range": [float(p.min()), float(p.max())],
        "poor_overlap_fraction": fraction,
        "warnings": (
            ["Poor empirical overlap: estimates rely on extrapolation"]
            if fraction > 0.1
            else []
        ),
        "assumptions": "Causal interpretation requires no unmeasured confounding, positivity, consistency, and a correct linear additive outcome model. Interval uses HC1 robust variance and a normal approximation; small samples are exploratory.",
    }


app = FastAPI(title="CausalLab", version="0.4.0")


STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/guide")
def user_guide():
    return FileResponse(
        Path(__file__).parent / "USER_GUIDE.md", media_type="text/plain"
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def run_analysis(req: Request):
    try:
        result = analyze(req)

        def check(value):
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("numeric overflow; rescale input values")
            if isinstance(value, dict):
                for item in value.values():
                    check(item)
            elif isinstance(value, list):
                for item in value:
                    check(item)

        check(result)
        return result
    except (ValueError, np.linalg.LinAlgError, OverflowError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


app.add_middleware(InputGuard)


app.add_middleware(AccessControl)
