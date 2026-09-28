import asyncio
import hashlib
import json
import math
import statistics
import time
import uuid
import httpx
from .models import Dataset
from .scoring import SCORER_VERSION, score_answer
from .store import now


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def new_run(store, dataset, version, timeout):
    data = dataset.model_dump()
    run = {'id': uuid.uuid4().hex, 'created_at': now(), 'dataset': data, 'dataset_hash': digest(data),
           'version': version, 'prompt_hash': digest(version), 'scorer_version': SCORER_VERSION,
           'timeout_seconds': timeout, 'is_demo': version['provider'] == 'demo'}
    store.add_run(run)
    return run['id']


async def execute(store, run_id, provider):
    from .providers import MalformedResponse, ProviderError
    run = store.get_run(run_id)
    store.status(run_id, 'running')
    try:
        for case in Dataset.model_validate(run['dataset']).cases:
            started = time.perf_counter()
            answer, error, status = '', None, 'ok'
            try:
                answer = await asyncio.wait_for(provider.answer(run['version'], case, run['timeout_seconds']), run['timeout_seconds'])
                if not isinstance(answer, str):
                    raise MalformedResponse('Answer must be a string')
                if not answer.strip():
                    status, error = 'empty', 'Provider returned an empty answer'
            except (TimeoutError, httpx.TimeoutException):
                status, error = 'timeout', 'Request deadline exceeded'
            except MalformedResponse:
                status, error = 'malformed', 'Response did not satisfy the adapter contract'
            except (httpx.HTTPError, ProviderError):
                status, error = 'error', 'Provider request failed; check endpoint configuration and service health'
            elapsed = (time.perf_counter() - started) * 1000
            result = {'case_id': case.id, 'question': case.question, 'category': case.category,
                      'answer': answer, 'status': status, 'error': error, 'latency_ms': round(elapsed, 3),
                      **score_answer(case, answer)}
            if status != 'ok':
                result['score'], result['passed'] = 0, False
            store.add_result(run_id, result)
        store.status(run_id, 'completed')
    except asyncio.CancelledError:
        store.status(run_id, 'interrupted', 'Run was cancelled during process shutdown')
        raise
    except Exception:
        # A platform error fails the RUN rather than masquerading as a model failure.
        store.status(run_id, 'failed', 'Internal evaluation error; inspect server logs')
        raise


def summary(run):
    results = run['results']
    latency = sorted(r['latency_ms'] for r in results)
    return {'total': len(results), 'passed': sum(r['passed'] for r in results),
            'mean_score': round(statistics.mean(r['score'] for r in results), 4) if results else 0,
            'failures': sum(not r['passed'] for r in results),
            'provider_failures': sum(r['status'] != 'ok' for r in results),
            'median_ms': round(statistics.median(latency), 3) if latency else 0,
            'p95_ms': latency[math.ceil(len(latency) * .95) - 1] if latency else 0}


def compare(baseline, candidate):
    if baseline['status'] != 'completed' or candidate['status'] != 'completed':
        raise ValueError('Only completed runs can be compared')
    for key in ['dataset_hash', 'scorer_version']:
        if baseline[key] != candidate[key]:
            raise ValueError(f'Incompatible {key}; rerun both versions on the same dataset and scorer')
    a = {r['case_id']: r for r in baseline['results']}
    b = {r['case_id']: r for r in candidate['results']}
    expected = {c['id'] for c in baseline['dataset']['cases']}
    if set(a) != expected or set(b) != expected:
        raise ValueError('Run is missing expected results')
    rows = []
    for case_id in a:
        before, after = a[case_id], b[case_id]
        delta = round(after['score'] - before['score'], 4)
        # An infrastructure failure is regression even when both scores were already zero.
        worse = delta < 0 or (before['status'] == 'ok' and after['status'] != 'ok')
        better = delta > 0 or (before['status'] != 'ok' and after['status'] == 'ok')
        change = 'regressed' if worse else 'improved' if better else 'unchanged'
        rows.append({'case_id': case_id, 'question': after['question'], 'category': after['category'],
                     'case_definition': next(c for c in candidate['dataset']['cases'] if c['id'] == case_id),
                     'change': change, 'score_delta': delta, 'latency_delta_ms': round(after['latency_ms'] - before['latency_ms'], 3),
                     'baseline': before, 'candidate': after})
    return {'baseline_id': baseline['id'], 'candidate_id': candidate['id'],
            'dataset_version': baseline['dataset']['version'], 'dataset_hash': baseline['dataset_hash'],
            'scorer_version': baseline['scorer_version'], 'is_demo': baseline['is_demo'] or candidate['is_demo'],
            'settings_differ': baseline['timeout_seconds'] != candidate['timeout_seconds'],
            'baseline_summary': summary(baseline), 'candidate_summary': summary(candidate),
            'counts': {c: sum(r['change'] == c for r in rows) for c in ['improved', 'regressed', 'unchanged']}, 'rows': rows}
