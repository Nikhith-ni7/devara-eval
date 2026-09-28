import asyncio
import json
import httpx
import pytest
from app.providers import Provider, MalformedResponse, ProviderError
from app.engine import execute, new_run
from app.models import Dataset


def test_devara_contract_and_auth(monkeypatch,dataset,versions):
    monkeypatch.setenv('DEVARA_URL','http://devara.test/answer')
    monkeypatch.setenv('DEVARA_API_KEY','test-only-key')
    def handler(request):
        body=json.loads(request.content)
        assert body['question']==dataset.cases[0].question
        assert body['system_prompt']==versions['devara-baseline-v1']['system_prompt']
        assert body['prompt_version']=='devara-baseline-v1'
        assert request.headers['authorization']=='Bearer test-only-key'
        assert 'facts' not in body
        return httpx.Response(200,json={'response':'A valid answer.'})
    adapter=Provider(httpx.MockTransport(handler))
    assert asyncio.run(adapter.answer(versions['devara-baseline-v1'],dataset.cases[0],1))=='A valid answer.'


def test_ollama_contract(monkeypatch,dataset,versions):
    monkeypatch.setenv('OLLAMA_URL','http://ollama.test/api/chat')
    def handler(request):
        body=json.loads(request.content)
        assert body['stream'] is False
        assert body['options']['seed']==42
        assert body['messages'][1]['content']==dataset.cases[0].question
        return httpx.Response(200,json={'message':{'content':'Hello'}})
    assert asyncio.run(Provider(httpx.MockTransport(handler)).answer(versions['ollama-baseline-v1'],dataset.cases[0],1))=='Hello'


@pytest.mark.parametrize('payload',[{}, {'response':None},{'response':[]},[],{'response':123}])
def test_malformed_json_shapes(monkeypatch,dataset,versions,payload):
    monkeypatch.setenv('DEVARA_URL','http://devara.test/answer')
    adapter=Provider(httpx.MockTransport(lambda _:httpx.Response(200,json=payload)))
    with pytest.raises(MalformedResponse):asyncio.run(adapter.answer(versions['devara-baseline-v1'],dataset.cases[0],1))


def test_invalid_json(monkeypatch,dataset,versions):
    monkeypatch.setenv('DEVARA_URL','http://devara.test/answer')
    adapter=Provider(httpx.MockTransport(lambda _:httpx.Response(200,text='{bad json')))
    with pytest.raises(MalformedResponse):asyncio.run(adapter.answer(versions['devara-baseline-v1'],dataset.cases[0],1))


def test_response_size_limit(monkeypatch,dataset,versions):
    monkeypatch.setenv('DEVARA_URL','http://devara.test/answer')
    adapter=Provider(httpx.MockTransport(lambda _:httpx.Response(200,content=b'x'*1_000_001)))
    with pytest.raises(MalformedResponse):asyncio.run(adapter.answer(versions['devara-baseline-v1'],dataset.cases[0],1))


@pytest.mark.parametrize('mode,expected',[('timeout','timeout'),('503','error'),('malformed','malformed')])
def test_real_adapter_failure_recovery(monkeypatch,store,dataset,versions,mode,expected):
    monkeypatch.setenv('DEVARA_URL','http://devara.test/answer')
    count=0
    def handler(request):
        nonlocal count
        count+=1
        if count==1:
            if mode=='timeout':raise httpx.ReadTimeout('private endpoint info')
            if mode=='503':return httpx.Response(503,text='secret error body')
            return httpx.Response(200,text='not-json')
        return httpx.Response(200,json={'response':'This is a valid response after the failed call.'})
    mini=Dataset(version='mini',cases=dataset.cases[:2])
    run_id=new_run(store,mini,versions['devara-baseline-v1'],1)
    asyncio.run(execute(store,run_id,Provider(httpx.MockTransport(handler))))
    run=store.get_run(run_id)
    assert run['status']=='completed'
    assert run['results'][0]['status']==expected
    assert run['results'][1]['status']=='ok'
    assert 'secret' not in json.dumps(run)
    assert 'private endpoint info' not in json.dumps(run)


def test_missing_devara_configuration(monkeypatch,dataset,versions):
    monkeypatch.delenv('DEVARA_URL',raising=False)
    with pytest.raises(ProviderError):asyncio.run(Provider().answer(versions['devara-baseline-v1'],dataset.cases[0],1))
