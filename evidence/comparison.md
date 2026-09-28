# Devara Eval comparison report

**Synthetic fixtures with intentionally injected faults. Not measured Devara model quality.**

Dataset: `programming-v1.0.0`
Dataset SHA-256: `c74f0d58cb80c21b4f0edd3488894a315892506482b6d67e10c69c47342772b1`
Scorer: `lexical-v1`

| Measurement | Baseline | Candidate |
|---|---:|---:|
| Cases passing every check | 42/50 | 45/50 |
| Mean check-completion score | 0.8770 | 0.9050 |
| Provider failures (including empty) | 0 | 4 |
| Median observed latency (ms) | 2.114 | 2.115 |
| P95 observed latency (ms) | 2.169 | 2.159 |

Changes: 8 improved, 5 regressed, 37 unchanged.

## Changed cases

| Case | Change | Baseline score | Candidate score | Candidate status |
|---|---|---:|---:|---|
| prog-002 | improved | 0.2 | 1.0 | ok |
| prog-004 | regressed | 1.0 | 0.25 | ok |
| prog-007 | improved | 0.25 | 1.0 | ok |
| prog-012 | improved | 0.25 | 1.0 | ok |
| prog-014 | regressed | 1.0 | 0 | timeout |
| prog-017 | improved | 0.25 | 1.0 | ok |
| prog-022 | improved | 0.2 | 1.0 | ok |
| prog-024 | regressed | 1.0 | 0 | malformed |
| prog-027 | improved | 0.25 | 1.0 | ok |
| prog-032 | improved | 0.2 | 1.0 | ok |
| prog-034 | regressed | 1.0 | 0 | empty |
| prog-037 | improved | 0.25 | 1.0 | ok |
| prog-044 | regressed | 1.0 | 0 | error |

## Interpretation

A score is the fraction of lexical/format checks passed; all checks must pass for a case to pass. Provider failures force score zero. A score decrease or a new provider failure is a regression. Partial improvements may still fail the case.

Latency uses monotonic wall-clock time including provider failure waits. P95 uses nearest rank. One sequential sample per question is descriptive, not a statistical performance claim. No human reviews were automatically fabricated. Consult the raw run exports and human-review rubric before judging correctness.

Reproduce the fixture scenario with `python -m app.cli demo --out evidence/reproduced`. Latencies, timestamps, and run IDs will vary.
