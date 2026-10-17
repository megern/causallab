import math
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import app

from app.main import covariate_balance


def request_payload():
    confounders = [1, 2, 3, 4, 5, 2, 3, 4, 5, 6]
    treatment = [0] * 5 + [1] * 5
    return {
        "outcome": [2 * x + 3 * t for x, t in zip(confounders, treatment)],
        "treatment": treatment,
        "confounders": [[x] for x in confounders],
        "confounder_names": ["Baseline"],
    }


def test_raw_group_balance_known_sample_standardization():
    response = TestClient(app).post("/analyze", json=request_payload())
    assert response.status_code == 200, response.text
    result = response.json()
    balance = result["covariate_balance"][0]
    assert result["group_counts"] == {"control": 5, "treated": 5}
    assert balance["confounder"] == "Baseline"
    assert balance["control_mean"] == 3 and balance["treated_mean"] == 4
    assert balance["pooled_sample_sd"] == pytest.approx(math.sqrt(2.5))
    assert balance["standardized_mean_difference"] == pytest.approx(1 / math.sqrt(2.5))
    assert balance["descriptive_imbalance_flag"] is True
    assert result["treatment_effect"] == pytest.approx(3)
    assert len(result["approximate_95_percent_interval"]) == 2
    assert "not a claim that OLS balanced" in result["balance_method"]


def test_unequal_groups_use_pooled_sample_degrees_of_freedom():
    values = np.asarray([[0], [1], [2], [2], [4], [6], [8]], dtype=float)
    balance = covariate_balance(values, np.asarray([0, 0, 0, 1, 1, 1, 1]), ["x"])[0]
    assert balance["pooled_sample_sd"] == pytest.approx(math.sqrt(4.4))
    assert balance["standardized_mean_difference"] == pytest.approx(4 / math.sqrt(4.4))


def test_zero_variance_diagnostic_is_explicit():
    treatment = np.asarray([0] * 3 + [1] * 3)
    equal = covariate_balance(np.ones((6, 1)), treatment, ["x"])[0]
    assert equal["zero_pooled_variance"] and equal["standardized_mean_difference"] == 0
    separated = covariate_balance(np.asarray([[0]] * 3 + [[1]] * 3), treatment, ["x"])[
        0
    ]
    assert separated["standardized_mean_difference"] is None
    assert separated["descriptive_imbalance_flag"] is True


@pytest.mark.parametrize("names", [[], [""], ["x", "y"], [" " * 2], ["x" * 101]])
def test_bad_confounder_names_rejected(names):
    data = request_payload()
    data["confounder_names"] = names
    assert TestClient(app).post("/analyze", json=data).status_code == 422


def test_unnamed_request_backwards_compatible():
    data = request_payload()
    del data["confounder_names"]
    response = TestClient(app).post("/analyze", json=data)
    assert response.status_code == 200
    assert response.json()["covariate_balance"][0]["confounder"] == "confounder_0"
