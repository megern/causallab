import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import Request, analyze, app


def test_adjusts_known_confounder():
    rng = np.random.default_rng(7)
    c = rng.normal(size=1000)
    t = rng.binomial(1, 1 / (1 + np.exp(-c)))
    y = 3 * t + 5 * c + rng.normal(0, 0.05, 1000)
    result = analyze(
        Request(
            outcome=y.tolist(), treatment=t.tolist(), confounders=c[:, None].tolist()
        )
    )
    assert result["treatment_effect"] == pytest.approx(3, abs=0.02)
    assert result["robust_standard_error"] > 0


def test_collinearity():
    with pytest.raises(ValueError, match="collinear"):
        analyze(
            Request(
                outcome=list(range(10)),
                treatment=[0] * 5 + [1] * 5,
                confounders=[[0]] * 5 + [[1]] * 5,
            )
        )


def test_api_and_ui():
    import json
    from pathlib import Path

    client = TestClient(app)
    payload = json.loads(
        (Path(__file__).parents[1] / "examples/synthetic.json").read_text()
    )
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), dict)
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/").status_code == 200
    assert client.post("/analyze", json={}).status_code == 422


def test_nonfinite_rejected():
    import json
    from pathlib import Path

    payload = json.loads(
        (Path(__file__).parents[1] / "examples/synthetic.json").read_text()
    )
    key = next(iter(payload))
    if isinstance(payload[key][0], list):
        payload[key][0][0] = "nan"
    else:
        payload[key][0] = "nan"
    assert TestClient(app).post("/analyze", json=payload).status_code == 422


def test_separated_treatment_reports_overlap_risk():
    c = np.linspace(-3, 3, 100)
    t = (c > 0).astype(int)
    result = analyze(
        Request(
            outcome=(2 * t + c).tolist(),
            treatment=t.tolist(),
            confounders=c[:, None].tolist(),
        )
    )
    assert result["poor_overlap_fraction"] > 0.1
    assert result["warnings"]
    assert result["treatment_effect"] == pytest.approx(2)


def test_treatment_and_ragged_data_rejected():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Request(outcome=list(range(10)), treatment=[0] * 10, confounders=[[1]] * 10)
    with pytest.raises(ValidationError):
        Request(
            outcome=list(range(10)),
            treatment=[0] * 5 + [1] * 5,
            confounders=[[1], [1, 2]] * 5,
        )
