import numpy as np
from fastapi.testclient import TestClient
from app.main import Request, analyze, app

def test_reviewer_balanced_identified_effect():
    # Identical covariate distribution per group removes confounding.
    c=np.tile(np.arange(6),2).astype(float)
    t=np.repeat([0,1],6)
    y=7+2*c+4*t
    r=analyze(Request(outcome=y.tolist(),treatment=t.tolist(),confounders=c[:,None].tolist()))
    assert abs(r['treatment_effect']-4)<1e-10
    assert r['robust_standard_error']<1e-10
    assert np.allclose(r['propensity_range'],[.5,.5])

def test_reviewer_hc1_against_independent_sandwich():
    c=np.tile(np.arange(8),2).astype(float);t=np.repeat([0,1],8)
    noise=np.array([1,-1,2,-2,1,-1,3,-3,2,-2,1,-1,3,-3,1,-1])
    y=2+c+3*t+noise
    x=np.column_stack([np.ones(16),t,c])
    beta=np.linalg.pinv(x)@y; e=y-x@beta
    influence=np.linalg.pinv(x)*e[None,:]
    expected=np.sqrt((influence@influence.T)[1,1]*16/13)
    r=analyze(Request(outcome=y.tolist(),treatment=t.tolist(),confounders=c[:,None].tolist()))
    assert np.isclose(r['robust_standard_error'],expected)
    assert r['approximate_95_percent_interval'][0] <= r['treatment_effect'] <= r['approximate_95_percent_interval'][1]

def test_reviewer_collinearity_is_rejected():
    t=[0]*6+[1]*6
    r=TestClient(app).post('/analyze',json={'outcome':list(range(12)),'treatment':t,'confounders':[[v] for v in t]})
    assert r.status_code==422

def test_reviewer_finite_extreme_outcomes_must_not_hide_nan_variance():
    import numpy as np
    rng=np.random.default_rng(973)
    c=rng.normal(size=(100,3)).tolist()
    t=rng.binomial(1,.5,100).tolist()
    y=[1e308 if i%2==0 else -1e308 for i in range(100)]
    r=TestClient(app).post('/analyze',json={'outcome':y,'treatment':t,'confounders':c})
    assert r.status_code==422
