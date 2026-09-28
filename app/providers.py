import asyncio
import os
import httpx
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


class MalformedResponse(Exception):
    pass


class ProviderError(Exception):
    pass


class Provider:
    """Endpoints/credentials are server-configured, never accepted from browser input."""
    def __init__(self, transport=None):
        self.transport = transport
        self.fixtures = json.loads((ROOT / 'data/demo_answers.json').read_text())

    async def answer(self, version, case, timeout):
        if version['provider'] == 'demo':
            return await self.demo(version, case, timeout)
        provider = version['provider']
        env = 'OLLAMA_URL' if provider == 'ollama' else 'DEVARA_URL'
        endpoint = os.getenv(env, 'http://127.0.0.1:11434/api/chat' if provider == 'ollama' else '')
        if not endpoint:
            raise ProviderError('Devara endpoint is not configured')
        headers = {}
        if provider == 'devara' and os.getenv('DEVARA_API_KEY'):
            headers['Authorization'] = f"Bearer {os.environ['DEVARA_API_KEY']}"
        messages = [{'role': 'system', 'content': version['system_prompt']}, {'role': 'user', 'content': case.question}]
        if provider == 'ollama':
            body = {'model': version['model'], 'messages': messages, 'stream': False,
                    'options': {'temperature': version['temperature'], 'seed': version['seed']}}
        else:
            body = {'question': case.question, 'system_prompt': version['system_prompt'],
                    'prompt_version': version['id'], 'model': version['model'],
                    'temperature': version['temperature'], 'seed': version['seed']}
        async with httpx.AsyncClient(timeout=timeout, transport=self.transport, follow_redirects=False) as client:
            async with client.stream('POST', endpoint, json=body, headers=headers) as response:
                response.raise_for_status()
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > 1_000_000:
                        raise MalformedResponse('Response exceeded 1 MB')
        try:
            payload = json.loads(data)
            answer = payload['message']['content'] if provider == 'ollama' else payload['response']
        except (ValueError, KeyError, TypeError) as exc:
            raise MalformedResponse('Invalid JSON or missing answer field') from exc
        if not isinstance(answer, str):
            raise MalformedResponse('Answer must be a string')
        return answer

    async def demo(self, version, case, timeout):
        # Intentional fixture faults, not model measurements. Never used by real adapters.
        await asyncio.sleep(0.002)
        number = int(case.id.split('-')[-1])
        if version['demo_variant'] == 'baseline' and number in {2, 7, 12, 17, 22, 27, 32, 37}:
            return 'I am not sure.'
        if version['demo_variant'] == 'candidate':
            if number == 4:
                return 'A tuple can change freely.'
            if number == 14:
                await asyncio.sleep(timeout + 0.1)
            if number == 24:
                raise MalformedResponse('Injected malformed response')
            if number == 34:
                return ''
            if number == 44:
                raise ProviderError('Injected provider failure')
        return self.fixtures[case.id]
