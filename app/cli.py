"""Run evaluations and export evidence without the dashboard."""
import argparse
import asyncio
import json
from pathlib import Path
from .engine import compare, execute, new_run, summary
from .main import ROOT
from .models import Dataset, Version
from .providers import Provider
from .store import Store


def markdown(report):
    a, b = report['baseline_summary'], report['candidate_summary']
    lines = ['# Devara Eval comparison report', '',
             '**Synthetic fixtures with intentionally injected faults. Not measured Devara model quality.**' if report['is_demo'] else '**Live adapter evaluation. Lexical check scores are not semantic accuracy.**', '',
             f"Dataset: `{report['dataset_version']}`", f"Dataset SHA-256: `{report['dataset_hash']}`", f"Scorer: `{report['scorer_version']}`", '',
             '| Measurement | Baseline | Candidate |', '|---|---:|---:|',
             f"| Cases passing every check | {a['passed']}/{a['total']} | {b['passed']}/{b['total']} |",
             f"| Mean check-completion score | {a['mean_score']:.4f} | {b['mean_score']:.4f} |",
             f"| Provider failures (including empty) | {a['provider_failures']} | {b['provider_failures']} |",
             f"| Median observed latency (ms) | {a['median_ms']} | {b['median_ms']} |",
             f"| P95 observed latency (ms) | {a['p95_ms']} | {b['p95_ms']} |", '',
             f"Changes: {report['counts']['improved']} improved, {report['counts']['regressed']} regressed, {report['counts']['unchanged']} unchanged.", '',
             '## Changed cases', '', '| Case | Change | Baseline score | Candidate score | Candidate status |', '|---|---|---:|---:|---|']
    for row in report['rows']:
        if row['change'] != 'unchanged':
            lines.append(f"| {row['case_id']} | {row['change']} | {row['baseline']['score']} | {row['candidate']['score']} | {row['candidate']['status']} |")
    lines += ['', '## Interpretation', '',
              'A score is the fraction of lexical/format checks passed; all checks must pass for a case to pass. Provider failures force score zero. A score decrease or a new provider failure is a regression. Partial improvements may still fail the case.', '',
              'Latency uses monotonic wall-clock time including provider failure waits. P95 uses nearest rank. One sequential sample per question is descriptive, not a statistical performance claim. No human reviews were automatically fabricated. Consult the raw run exports and human-review rubric before judging correctness.', '',
              'Reproduce the fixture scenario with `python -m app.cli demo --out evidence/reproduced`. Latencies, timestamps, and run IDs will vary.']
    if report['settings_differ']:
        lines += ['', '**Request deadlines differ between runs; compare timing and failures cautiously.**']
    return '\n'.join(lines) + '\n'


async def main_async(args):
    store = Store(args.db)
    dataset = Dataset.model_validate_json((ROOT / 'data/programming-v1.json').read_text())
    versions = [Version.model_validate(v).model_dump() for v in json.loads((ROOT / 'prompts/versions.json').read_text())]
    for version in versions:
        if not store.version(version['id']):
            store.add_version(version)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.command == 'compare':
        a, b = store.get_run(args.baseline), store.get_run(args.candidate)
        if not a or not b:
            raise ValueError('Run not found')
        report = compare(a, b)
    elif args.command == 'demo':
        ids = []
        for name in ['demo-baseline-v1', 'demo-candidate-v1']:
            run_id = new_run(store, dataset, store.version(name), .25)
            await execute(store, run_id, Provider())
            ids.append(run_id)
        a, b = (store.get_run(i) for i in ids)
        report = compare(a, b)
    else:
        version = store.version(args.version)
        if not version:
            raise ValueError('Version not found')
        run_id = new_run(store, dataset, version, args.timeout)
        await execute(store, run_id, Provider())
        run = store.get_run(run_id)
        (out / f'run-{run_id}.json').write_text(json.dumps(run, indent=2) + '\n')
        print(json.dumps({'id': run_id, 'summary': summary(run)}, indent=2))
        return 0
    for name, run in [('baseline', a), ('candidate', b)]:
        (out / f'{name}-run.json').write_text(json.dumps(run, indent=2) + '\n')
    (out / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    (out / 'comparison.md').write_text(markdown(report))
    print(json.dumps(report['counts'], indent=2))
    return 1 if getattr(args, 'fail_on_regression', False) and report['counts']['regressed'] else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['demo', 'run', 'compare'])
    parser.add_argument('--db', default=str(ROOT / 'storage/eval.sqlite3'))
    parser.add_argument('--out', default=str(ROOT / 'evidence'))
    parser.add_argument('--version', default='demo-baseline-v1')
    parser.add_argument('--timeout', type=float, default=30)
    parser.add_argument('--baseline')
    parser.add_argument('--candidate')
    parser.add_argument('--fail-on-regression', action='store_true')
    args = parser.parse_args()
    if not .01 <= args.timeout <= 120:
        parser.error('timeout must be between .01 and 120 seconds')
    if args.command == 'compare' and (not args.baseline or not args.candidate):
        parser.error('compare requires --baseline and --candidate')
    try:
        raise SystemExit(asyncio.run(main_async(args)))
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
