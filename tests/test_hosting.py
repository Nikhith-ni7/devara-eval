import base64
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.hosting import Hosting

TEST_PASSWORD = 'this-is-only-a-test-password'


@pytest.fixture
def hosted_env(monkeypatch):
    monkeypatch.setenv('EVAL_HOSTED', '1')
    monkeypatch.setenv('EVAL_PASSWORD', TEST_PASSWORD)
    monkeypatch.setenv('EVAL_USERNAME', 'owner')
    monkeypatch.setenv('RENDER_EXTERNAL_HOSTNAME', 'devara-example.onrender.com')
    monkeypatch.setenv('EVAL_STORAGE_EPHEMERAL', '1')


def test_hosted_fails_closed_without_password(monkeypatch,tmp_path):
    monkeypatch.setenv('EVAL_HOSTED','1')
    monkeypatch.delenv('EVAL_PASSWORD',raising=False)
    with pytest.raises(ValueError,match='EVAL_PASSWORD'):
        create_app(tmp_path/'fail.sqlite3')


def test_render_automatically_requires_auth(monkeypatch,tmp_path):
    monkeypatch.setenv('RENDER','true')
    monkeypatch.delenv('EVAL_HOSTED',raising=False)
    monkeypatch.delenv('EVAL_PASSWORD',raising=False)
    with pytest.raises(ValueError,match='EVAL_PASSWORD'):
        create_app(tmp_path/'fail.sqlite3')


def test_hosted_routes_and_origins(hosted_env,tmp_path):
    app=create_app(tmp_path/'hosted.sqlite3')
    with TestClient(app,base_url='https://devara-example.onrender.com') as client:
        assert client.get('/api/health').status_code==200
        for path in ['/', '/api/runs','/api/config','/docs','/openapi.json']:
            response=client.get(path)
            assert response.status_code==401
            assert response.headers['www-authenticate'].startswith('Basic')
        assert client.get('/api/runs',auth=('owner','wrong')).status_code==401
        client.auth=('owner',TEST_PASSWORD)
        assert client.get('/api/runs').status_code==200
        assert client.get('/').status_code==200
        config=client.get('/api/config')
        assert config.json()=={'hosted':True,'ephemeral_storage':True}
        assert config.headers['cache-control']=='private, no-store'
        assert TEST_PASSWORD not in config.text
        data={'id':'host-test','provider':'demo','model':'fixture','system_prompt':'A new prompt.'}
        assert client.post('/api/versions',json=data,headers={'Origin':'https://devara-example.onrender.com'}).status_code==201
        assert client.post('/api/versions',json={**data,'id':'blocked'},headers={'Origin':'https://evil.example'}).status_code==403
        assert client.post('/api/versions',json={**data,'id':'blocked'},headers={'Sec-Fetch-Site':'cross-site'}).status_code==403
        assert client.get('/api/health',headers={'Host':'evil.example'}).status_code==400


@pytest.mark.parametrize('header',['Basic nonsense','Bearer token','Basic '+base64.b64encode(b'no-colon').decode(),'Basic /w==',''])
def test_malformed_auth_fails(hosted_env,header):
    assert not Hosting.from_environment().authenticated(header)


def test_custom_domain_allowlist(hosted_env,monkeypatch):
    monkeypatch.setenv('EVAL_PUBLIC_URL','https://eval.example.com')
    config=Hosting.from_environment()
    assert 'eval.example.com' in config.hosts
    assert 'https://eval.example.com' in config.origins
    monkeypatch.setenv('EVAL_PUBLIC_URL','https://eval.example.com/unsafe/path')
    with pytest.raises(ValueError):Hosting.from_environment()
