import time
from fastapi.testclient import TestClient
import pytest
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path/'api.sqlite3')) as c:
        yield c


def wait_for_run(client,run_id):
    for _ in range(200):
        run=client.get(f'/api/runs/{run_id}').json()
        if run['status'] in {'completed','failed','interrupted'}:return run
        time.sleep(.01)
    raise AssertionError('Run did not complete')


def test_api_run_export_and_review(client):
    assert client.get('/api/health').status_code==200
    assert len(client.get('/api/dataset').json()['cases'])==50
    response=client.post('/api/runs',json={'version_id':'demo-baseline-v1','timeout_seconds':.25})
    assert response.status_code==202
    run=wait_for_run(client,response.json()['id'])
    assert run['status']=='completed'
    assert run['summary']['passed']==42
    review={'reviewer':'Tester','correctness':2,'completeness':1,'clarity':2,'notes':'Needs a nested-list example.'}
    assert client.post(f"/api/runs/{run['id']}/reviews/prog-001",json=review).status_code==201
    export=client.get(f"/api/runs/{run['id']}/export")
    assert export.json()['reviews'][0]['notes']==review['notes']
    assert export.json()['summary']==run['summary']
    assert 'attachment' in export.headers['content-disposition']
    assert client.post(f"/api/runs/{run['id']}/reviews/absent",json=review).status_code==404


def test_versions_are_immutable(client,versions):
    v=versions['demo-baseline-v1'];v['id']='custom-v1'
    assert client.post('/api/versions',json=v).status_code==201
    assert client.post('/api/versions',json=v).status_code==409
    assert client.get('/api/versions').status_code==200


@pytest.mark.parametrize('body',[{'version_id':'demo-baseline-v1','timeout_seconds':0},{'version_id':'demo-baseline-v1','timeout_seconds':121},{'version_id':'demo-baseline-v1','url':'http://untrusted'}])
def test_invalid_run_request(client,body):
    assert client.post('/api/runs',json=body).status_code==422


def test_missing_resources_and_config(client,monkeypatch):
    monkeypatch.delenv('DEVARA_URL',raising=False)
    assert client.get('/api/runs/missing').status_code==404
    assert client.post('/api/runs',json={'version_id':'missing'}).status_code==404
    assert client.post('/api/runs',json={'version_id':'devara-baseline-v1'}).status_code==422


def test_cross_origin_write_rejected(client):
    assert client.post('/api/runs',json={'version_id':'demo-baseline-v1'},headers={'Origin':'https://untrusted.example'}).status_code==403


def test_queue_bound_and_live_comparison_rejected(tmp_path):
    import asyncio
    class Slow:
        async def answer(self,*args):
            await asyncio.sleep(10)
            return 'done'
    with TestClient(create_app(tmp_path/'queue.sqlite3',provider=Slow())) as c:
        ids=[c.post('/api/runs',json={'version_id':'demo-baseline-v1'}).json()['id'] for _ in range(4)]
        assert c.post('/api/runs',json={'version_id':'demo-baseline-v1'}).status_code==429
        assert c.get(f'/api/compare?baseline={ids[0]}&candidate={ids[1]}').status_code==409
