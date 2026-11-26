import pytest
from linebeads.entry import app
from linebeads.pipeline import execute, open_fixture, preview

ROUTE = '/api/linebeads'


def test_preset_workbench_has_real_business_rows():
    output = app.test_client().get(ROUTE+'/overview').get_json()
    assert len(output['metrics']) == 5 and len(output['sections']) == 8
    assert len(output['rows']) >= 10
    assert output['model'] == 'RBF 局部反光衰减回归'


def test_scenario_reallocates_business_capacity():
    test_client = app.test_client()
    tight = test_client.post(ROUTE+'/run',json={'capacity':1}).get_json()
    wide = test_client.post(ROUTE+'/run',json={'capacity':60,'strategy':'focus'}).get_json()
    assert tight['feature_stamp'] == wide['feature_stamp']
    assert tight['rows'] != wide['rows']
    assert tight['run_id'] != wide['run_id']


def test_windows_refuse_bad_document():
    response = app.test_client().post(ROUTE+'/run',json={'records':[{}]})
    assert response.status_code == 422 and response.get_json()['code'] == 'INVALID_BATCH'


def test_exact_health_and_template_match():
    test_client = app.test_client()
    assert test_client.get('/health').get_json() == {'status':'ok','service':'linebeads'}
    assert '夜间标线复测排班' in test_client.get('/').get_data(as_text=True)
    assert test_client.get('/static/desk.js').status_code == 200


def test_entered_data_matches_preset_when_identical():
    result = app.test_client().post(ROUTE+'/run',json=open_fixture())
    assert result.status_code == 200
    assert result.get_json()['run_id'] == preview()['run_id']


def test_input_order_cannot_change_disposition():
    dataset = open_fixture()
    forward = execute(dataset['records'])
    backward = execute(list(reversed(dataset['records'])))
    assert forward['run_id'] == backward['run_id']
    assert forward['rows'] == backward['rows']


def test_changed_profile_fetches_matching_stage():
    web = app.test_client()
    run = web.post(ROUTE+'/run',json={'capacity':6, 'strategy':'focus'}).get_json()
    found = web.get(ROUTE+'/stages/'+run['sections'][6]['key']+'?capacity=6&strategy=focus')
    assert found.status_code == 200
    assert found.get_json() == {**run['sections'][6],'run_id':run['run_id']}


@pytest.mark.parametrize('capacity',[0,True,61,None,'8',3.5])
def test_capacity_type_check(capacity):
    response = app.test_client().post(ROUTE+'/run',json={'capacity':capacity})
    assert response.status_code == 422
