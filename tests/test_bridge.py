import sys
import types
from fastapi.testclient import TestClient
from examples.devara_bridge import app


def test_bridge_calls_configured_bot_wrapper(monkeypatch):
    module=types.ModuleType('fake_bot_wrapper')
    async def answer(**kwargs):
        assert kwargs['question']=='Explain a tuple.'
        assert kwargs['system_prompt']=='Be accurate.'
        return 'A tuple is an immutable sequence.'
    module.answer=answer
    monkeypatch.setitem(sys.modules,'fake_bot_wrapper',module)
    monkeypatch.setenv('DEVARA_CALLABLE','fake_bot_wrapper:answer')
    monkeypatch.setenv('DEVARA_API_KEY','test-key')
    body={'question':'Explain a tuple.','system_prompt':'Be accurate.','prompt_version':'v1','model':'test','temperature':0,'seed':42}
    with TestClient(app) as c:
        assert c.post('/answer',json=body).status_code==401
        response=c.post('/answer',json=body,headers={'Authorization':'Bearer test-key'})
        assert response.status_code==200
        assert response.json()['response']=='A tuple is an immutable sequence.'
