"""Independent metamorphic checks of raw balance and adjusted-effect invariance."""
import math
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)


def payload():
    c=[-2,-1,0,1,2,3,-1,0,1,2,3,4]
    t=[0]*6+[1]*6
    return {'outcome':[2*x+3*z+0.2*math.sin(i) for i,(x,z) in enumerate(zip(c,t))], 'treatment':t,'confounders':[[x] for x in c],'confounder_names':['Synthetic baseline']}


def test_independent_confounder_units_change_smd_sign_not_effect_or_absolute_balance():
    data=payload();a=client.post('/analyze',json=data)
    assert a.status_code==200
    altered=deepcopy(data);altered['confounders']=[[-3*x[0]] for x in data['confounders']]
    b=client.post('/analyze',json=altered)
    assert b.status_code==200
    a,b=a.json(),b.json();left,right=a['covariate_balance'][0],b['covariate_balance'][0]
    assert right['standardized_mean_difference']==pytest.approx(-left['standardized_mean_difference'])
    assert right['pooled_sample_sd']==pytest.approx(left['pooled_sample_sd']*3)
    assert b['treatment_effect']==pytest.approx(a['treatment_effect'])
    assert b['robust_standard_error']==pytest.approx(a['robust_standard_error'])


def test_independent_relabeling_treatment_reverses_signed_effect_and_raw_balance():
    data=payload();a=client.post('/analyze',json=data).json()
    data['treatment']=[1-v for v in data['treatment']]
    b=client.post('/analyze',json=data).json()
    assert b['treatment_effect']==pytest.approx(-a['treatment_effect'])
    assert b['covariate_balance'][0]['standardized_mean_difference']==pytest.approx(-a['covariate_balance'][0]['standardized_mean_difference'])
    assert b['robust_standard_error']==pytest.approx(a['robust_standard_error'])
