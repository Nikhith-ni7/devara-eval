import asyncio
import copy
import pytest
from app.engine import compare, execute, new_run, summary
from app.models import Dataset
from app.providers import Provider, MalformedResponse, ProviderError
from app.store import Store


def run(store, dataset, version, adapter=None):
    run_id = new_run(store, dataset, version, .25)
    asyncio.run(execute(store, run_id, adapter or Provider()))
    return store.get_run(run_id)


def test_end_to_end_demo_catches_expected_changes(store, dataset, versions):
    baseline = run(store, dataset, versions['demo-baseline-v1'])
    candidate = run(store, dataset, versions['demo-candidate-v1'])
    report = compare(baseline, candidate)
    assert report['counts'] == {'improved': 8, 'regressed': 5, 'unchanged': 37}
    assert report['baseline_summary']['passed'] == 42
    assert report['candidate_summary']['passed'] == 45
    assert report['candidate_summary']['provider_failures'] == 4
    results = {r['case_id']: r for r in candidate['results']}
    assert results['prog-014']['status'] == 'timeout'
    assert results['prog-024']['status'] == 'malformed'
    assert results['prog-034']['status'] == 'empty'
    assert results['prog-044']['status'] == 'error'
    assert all(r['latency_ms'] >= 0 for r in results.values())
    assert len(Store(store.path).get_run(candidate['id'])['results']) == 50


@pytest.mark.parametrize('key,value',[('dataset_hash','different'),('scorer_version','v999'),('status','running')])
def test_incompatible_comparison_rejected(store,dataset,versions,key,value):
    baseline=run(store,Dataset(version='one',cases=dataset.cases[:1]),versions['demo-baseline-v1'])
    candidate=copy.deepcopy(baseline);candidate[key]=value
    with pytest.raises(ValueError):compare(baseline,candidate)


def test_missing_case_rejected(store,dataset,versions):
    baseline=run(store,Dataset(version='one',cases=dataset.cases[:1]),versions['demo-baseline-v1'])
    candidate=copy.deepcopy(baseline);candidate['results']=[]
    with pytest.raises(ValueError):compare(baseline,candidate)


def test_new_failure_at_zero_score_is_regression(store,dataset,versions):
    baseline=run(store,Dataset(version='one',cases=dataset.cases[:1]),versions['demo-baseline-v1'])
    baseline['results'][0].update(score=0,passed=False)
    candidate=copy.deepcopy(baseline);candidate['results'][0]['status']='timeout'
    assert compare(baseline,candidate)['counts']['regressed']==1


def test_snapshot_survives_source_mutation(store,dataset,versions):
    v=versions['demo-baseline-v1']
    run_id=new_run(store,dataset,v,.25)
    original=v['system_prompt'];v['system_prompt']='Changed'
    dataset.cases[0].question='Changed source question'
    saved=store.get_run(run_id)
    assert saved['version']['system_prompt']==original
    assert saved['dataset']['cases'][0]['question']!='Changed source question'


def test_recovery_marks_stale_runs_interrupted(store,dataset,versions):
    run_id=new_run(store,dataset,versions['demo-baseline-v1'],.25)
    store.recover()
    assert store.get_run(run_id)['status']=='interrupted'


def test_platform_bug_is_run_failure(store,dataset,versions):
    class Broken:
        async def answer(self,*args):raise RuntimeError('programmer bug')
    run_id=new_run(store,dataset,versions['demo-baseline-v1'],.25)
    with pytest.raises(RuntimeError):asyncio.run(execute(store,run_id,Broken()))
    assert store.get_run(run_id)['status']=='failed'


def test_p95_uses_nearest_rank():
    rows=[dict(latency_ms=i,passed=True,score=1,status='ok') for i in range(1,21)]
    assert summary({'results':rows})['p95_ms']==19
    assert summary({'results':rows})['median_ms']==10.5
