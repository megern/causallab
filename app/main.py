import math
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

    @model_validator(mode="after")
    def valid(self):
        matrix(self.confounders)
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
        return self


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
            break
    p = 1 / (1 + np.exp(-np.clip(z @ beta, -30, 30)))
    fraction = float(np.mean((p < 0.05) | (p > 0.95)))
    return {
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


app = FastAPI(title="CausalLab", version="0.2.0")


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


from .guard import InputGuard

app.add_middleware(InputGuard)
