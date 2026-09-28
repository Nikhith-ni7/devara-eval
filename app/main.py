import asyncio
import json
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .engine import compare, execute, new_run, summary
from .models import Dataset, Review, RunRequest, Version
from .providers import Provider
from .store import Store
from .hosting import Hosting

ROOT = Path(__file__).resolve().parents[1]


def create_app(db_path=None, provider=None, dataset_path=None):
    hosting = Hosting.from_environment()
    store = Store(db_path or os.getenv('EVAL_DB', str(ROOT / 'storage/eval.sqlite3')))
    dataset = Dataset.model_validate_json(Path(dataset_path or ROOT / 'data/programming-v1.json').read_text())
    adapter = provider or Provider()
    tasks = set()
    lock = asyncio.Lock()
    for item in json.loads((ROOT / 'prompts/versions.json').read_text()):
        v = Version.model_validate(item)
        if not store.version(v.id):
            store.add_version(v.model_dump())

    @asynccontextmanager
    async def lifespan(app):
        store.recover()
        yield
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(title='Devara Eval', version='1.1.0', lifespan=lifespan)
    app.state.store = store
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosting.hosts)

    @app.middleware('http')
    async def access_guard(request: Request, call_next):
        origin = request.headers.get('origin')
        if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
            if (origin and origin not in hosting.origins) or request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail': 'Cross-origin write rejected'}, status_code=403)
        health_check = request.method == 'GET' and request.url.path == '/api/health'
        if hosting.hosted and not health_check and not hosting.authenticated(request.headers.get('authorization')):
            return JSONResponse({'detail': 'Sign in to Devara Eval'}, status_code=401,
                                headers={'WWW-Authenticate': 'Basic realm="Devara Eval", charset="UTF-8"',
                                         'Cache-Control': 'no-store'})
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        if hosting.hosted:
            response.headers['Cache-Control'] = 'private, no-store'
        return response

    def get_run(run_id):
        run = store.get_run(run_id)
        if not run:
            raise HTTPException(404, 'Run not found')
        return run

    async def work(run_id):
        async with lock:
            await execute(store, run_id, adapter)

    def task_done(task):
        tasks.discard(task)
        if not task.cancelled() and task.exception():
            import logging
            logging.getLogger(__name__).error('Evaluation task failed', exc_info=task.exception())

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'dataset_version': dataset.version}

    @app.get('/api/config')
    def config():
        return {'hosted': hosting.hosted, 'ephemeral_storage': hosting.ephemeral}

    @app.get('/api/dataset')
    def get_dataset():
        return dataset

    @app.get('/api/versions')
    def versions():
        return store.versions()

    @app.post('/api/versions', status_code=201)
    def add_version(version: Version):
        try:
            store.add_version(version.model_dump())
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'Version ID exists; create a new immutable version')
        return version

    @app.post('/api/runs', status_code=202)
    async def start_run(body: RunRequest):
        version = store.version(body.version_id)
        if not version:
            raise HTTPException(404, 'Version not found')
        if len(tasks) >= 4:
            raise HTTPException(429, 'Run queue is full; wait for an active run to finish')
        if version['provider'] == 'devara' and not os.getenv('DEVARA_URL'):
            raise HTTPException(422, 'Set DEVARA_URL on the server before starting this version')
        run_id = new_run(store, dataset, version, body.timeout_seconds)
        task = asyncio.create_task(work(run_id))
        tasks.add(task)
        task.add_done_callback(task_done)
        return {'id': run_id, 'status': 'queued'}

    @app.get('/api/runs')
    def runs():
        return store.runs()

    @app.get('/api/runs/{run_id}')
    def run_detail(run_id: str):
        run = get_run(run_id)
        return {**run, 'summary': summary(run), 'reviews': store.reviews(run_id)}

    @app.get('/api/compare')
    def comparison(baseline: str, candidate: str):
        try:
            return compare(get_run(baseline), get_run(candidate))
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @app.get('/api/runs/{run_id}/export')
    def export(run_id: str):
        return JSONResponse(run_detail(run_id), headers={'Content-Disposition': f'attachment; filename="run-{run_id}.json"'})

    @app.post('/api/runs/{run_id}/reviews/{case_id}', status_code=201)
    def add_review(run_id: str, case_id: str, review: Review):
        run = get_run(run_id)
        if not any(r['case_id'] == case_id for r in run['results']):
            raise HTTPException(404, 'Result not found')
        return {'id': store.add_review(run_id, case_id, review.model_dump())}

    dist = ROOT / 'frontend/dist'
    if dist.exists():
        app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')

    @app.get('/')
    def home():
        if (dist / 'index.html').exists():
            return FileResponse(dist / 'index.html')
        return {'message': 'Build the dashboard: cd frontend && npm ci && npm run build', 'api_docs': '/docs'}

    return app
