import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_balanced_assignment_hajek_and_ess_known():
    x = np.tile(np.arange(5), 2)
    t = np.asarray([0] * 5 + [1] * 5)
    y = 2 * x + 3 * t
    response = TestClient(app).post(
        "/analyze",
        json={
            "outcome": y.tolist(),
            "treatment": t.tolist(),
            "confounders": x[:, None].tolist(),
            "include_ipw": True,
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    ipw = result["ipw"]
    assert ipw["ate"] == pytest.approx(3, abs=1e-7)
    assert ipw["effective_sample_size"] == pytest.approx({"control": 5, "treated": 5})
    assert ipw["weighted_balance"][0]["weighted_smd"] == pytest.approx(0, abs=1e-7)
    assert ipw["confidence_interval"] is None and ipw["clipped_observations"] == 0
    assert result["treatment_effect"] == pytest.approx(3)


def test_clipping_and_weighted_balance_are_explicit():
    x = np.linspace(-3, 3, 100)
    t = (x > 0).astype(int)
    y = x + 2 * t
    result = TestClient(app).post(
        "/analyze",
        json={
            "outcome": y.tolist(),
            "treatment": t.tolist(),
            "confounders": x[:, None].tolist(),
            "include_ipw": True,
            "propensity_clip": 0.1,
        },
    )
    assert result.status_code == 200, result.text
    ipw = result.json()["ipw"]
    assert ipw["clipped_observations"] > 0 and ipw["warnings"]
    assert 0 < ipw["effective_sample_size"]["treated"] <= 50


def test_ipw_optional_and_budget_checked():
    data = {
        "outcome": list(range(10)),
        "treatment": [0] * 5 + [1] * 5,
        "confounders": [[i % 5] for i in range(10)],
    }
    assert "ipw" not in TestClient(app).post("/analyze", json=data).json()
    data["include_ipw"] = True
    data["propensity_clip"] = 0
    assert TestClient(app).post("/analyze", json=data).status_code == 422


def test_ipw_row_budget_rejected_before_estimation():
    data = {
        "outcome": [0] * 5001,
        "treatment": [0] * 2500 + [1] * 2501,
        "confounders": [[i % 7] for i in range(5001)],
        "include_ipw": True,
    }
    response = TestClient(app).post("/analyze", json=data)
    assert response.status_code == 422
    assert "5000 rows" in response.text


def test_documented_synthetic_feature_request_is_runnable():
    import json
    from pathlib import Path

    data = json.loads(
        (Path(__file__).parents[1] / "examples/synthetic-ipw.json").read_text()
    )
    response = TestClient(app).post("/analyze", json=data)
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), dict)
