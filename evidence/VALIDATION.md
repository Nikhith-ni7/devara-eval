# Initial v1 delivery validation

For the latest v1.1 hosting checks, see HOSTING_VALIDATION.md. The results below describe the original local release.

Validated on Linux using Python 3.12.14, Node.js 24.19.0, and headless Chromium 153. Dependency versions are captured in `requirements.lock` and `frontend/package-lock.json`.

| Check | Observed outcome |
|---|---|
| Automated Python suite | 46 tests passed |
| Frontend production compilation | Passed; compiled assets included |
| Browser smoke scenario | Passed all 11 listed checks |
| Reference dataset validation | 50 unique programming cases; fixture answers satisfy declared checks |
| Synthetic baseline | 42 of 50 cases pass every deterministic check |
| Synthetic candidate | 45 of 50 cases pass every deterministic check |
| Comparison | 8 improved, 5 regressed, 37 unchanged |
| Injected provider failures | Timeout, malformed response, empty answer, provider error classified; later cases continue |
| CLI regression gate | Nonzero exit verified when requested and regressions exist |
| Devara bridge | Wrapper/authentication contract tested with a fake callable |
| Actual Devara model | Not connected or evaluated |
| Live Ollama model | Not downloaded or evaluated |
| macOS startup | Instructions supplied; execution environment was Linux |

Detailed output is in `pytest-results.txt`, `frontend-build.txt`, and `browser-smoke.txt`. The suite emitted one upstream Starlette deprecation warning about its TestClient HTTPX integration; it did not cause a failure. Coverage output does not include code executed by CLI subprocess tests, so the CLI's 0% line is not evidence that it was untested. No coverage percentage is presented as software correctness.

`baseline-run.json`, `candidate-run.json`, `comparison.json`, and `comparison.md` are outputs from an actual fixture execution. Timings were measured with a monotonic clock and will vary by machine. The model answers and fault patterns are synthetic; these files do not measure real Devara accuracy. No human judgments were added to those evidence exports.

Browser testing creates a separately labeled synthetic TEST review to verify persistence. Its temporary working database is excluded from the deliverable. Desktop and mobile screenshots are under `docs/` and may show different fixture run IDs/timings than the CLI report.
