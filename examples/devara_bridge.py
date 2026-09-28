"""Optional bridge; point DEVARA_CALLABLE at YOUR real bot wrapper."""
import hmac
import importlib
import inspect
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool


class Question(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=1, max_length=4000)
    system_prompt: str = Field(min_length=1, max_length=8000)
    prompt_version: str
    model: str
    temperature: float = Field(ge=0, le=2)
    seed: int


@asynccontextmanager
async def lifespan(app):
    spec = os.environ.get('DEVARA_CALLABLE', '')
    if ':' not in spec:
        raise RuntimeError('Set DEVARA_CALLABLE=your_module:your_wrapper_function')
    module, name = spec.split(':', 1)
    app.state.answer = getattr(importlib.import_module(module), name)
    if not callable(app.state.answer):
        raise RuntimeError('DEVARA_CALLABLE must name a callable')
    yield


app = FastAPI(title='Devara evaluation bridge', lifespan=lifespan)


@app.post('/answer')
async def answer(body: Question, authorization: str | None = Header(default=None)):
    key = os.getenv('DEVARA_API_KEY')
    if key and not hmac.compare_digest((authorization or '').encode(), f'Bearer {key}'.encode()):
        raise HTTPException(401, 'Invalid bearer token')
    fn = app.state.answer
    if inspect.iscoroutinefunction(fn):
        result = await fn(**body.model_dump())
    else:
        result = await run_in_threadpool(fn, **body.model_dump())
    if not isinstance(result, str):
        raise HTTPException(502, 'Bot wrapper must return a string')
    return {'response': result}
