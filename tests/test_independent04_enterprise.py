"""Independent scalar-score solution and Hájek accounting on synthetic strata."""

import math
import statistics
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ipw_clipping_hajek_ess_and_weighted_smd_against_scalar_score_solution():
    x = []
    t = []
    for value, treated in [(-1, 1), (0, 5), (1, 9)]:
        x.extend([value] * 10)
        t.extend([1] * treated + [0] * (10 - treated))
    y = [5 * group + v * v + 0.5 * v for v, group in zip(x, t)]
    # Symmetry gives zero intercept. Original-unit slope b satisfies the
    # regularized raw score 18 - 20*sigmoid(b) - .01*(2/3)*b = 0.
    lo, hi = 0.0, 10.0
    for _ in range(100):
        b = (lo + hi) / 2
        score = 18 - 20 / (1 + math.exp(-b)) - 0.01 * (2 / 3) * b
        if score > 0:
            lo = b
        else:
            hi = b
    b = (lo + hi) / 2
    p = [min(0.8, max(0.2, 1 / (1 + math.exp(-b * v)))) for v in x]
    weights = [1 / prob if group else 1 / (1 - prob) for prob, group in zip(p, t)]
    expected_means = {}
    expected_ess = {}
    covariate_means = {}
    for group, name in [(0, "control"), (1, "treated")]:
        indices = [i for i, z in enumerate(t) if z == group]
        total = math.fsum(weights[i] for i in indices)
        expected_means[name] = math.fsum(weights[i] * y[i] for i in indices) / total
        expected_ess[name] = total**2 / math.fsum(weights[i] ** 2 for i in indices)
        covariate_means[name] = math.fsum(weights[i] * x[i] for i in indices) / total
    x0 = [v for v, z in zip(x, t) if z == 0]
    x1 = [v for v, z in zip(x, t) if z == 1]
    sd = math.sqrt(
        (
            (len(x0) - 1) * statistics.variance(x0)
            + (len(x1) - 1) * statistics.variance(x1)
        )
        / (len(x) - 2)
    )
    response = client.post(
        "/analyze",
        json={
            "outcome": y,
            "treatment": t,
            "confounders": [[v] for v in x],
            "include_ipw": True,
            "propensity_clip": 0.2,
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()["ipw"]
    assert result["ate"] == pytest.approx(
        expected_means["treated"] - expected_means["control"], abs=1e-8
    )
    assert result["effective_sample_size"] == pytest.approx(expected_ess, abs=1e-8)
    assert result["weighted_balance"][0]["weighted_smd"] == pytest.approx(
        (covariate_means["treated"] - covariate_means["control"]) / sd, abs=1e-8
    )
    assert result["clipped_observations"] == 20 and result[
        "clipped_fraction"
    ] == pytest.approx(2 / 3)
    assert result["confidence_interval"] is None


def test_ipw_treatment_complement_reverses_effect_and_swaps_ess():
    x = [i % 7 - 3 for i in range(42)]
    t = [int((i * 13) % 11 < 5) for i in range(42)]
    y = [2 * z + v * 0.4 + v * v * 0.1 for v, z in zip(x, t)]
    base = {"outcome": y, "confounders": [[v] for v in x], "include_ipw": True}
    a = client.post("/analyze", json={**base, "treatment": t})
    b = client.post("/analyze", json={**base, "treatment": [1 - z for z in t]})
    assert a.status_code == b.status_code == 200
    a, b = a.json()["ipw"], b.json()["ipw"]
    assert a["ate"] == pytest.approx(-b["ate"], abs=1e-8)
    assert a["effective_sample_size"]["control"] == pytest.approx(
        b["effective_sample_size"]["treated"]
    )
