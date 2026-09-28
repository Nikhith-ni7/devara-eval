# Hosted-deployment preparation validation

The v1.1 hosting update passed **55 automated tests** and the complete browser smoke workflow with hosted-mode authentication enabled. React production compilation succeeded. Both YAML configuration files parsed successfully, and shell scripts passed bash syntax checks.

New checks cover startup refusal without a password, automatic hosted-mode detection on Render, authentication on protected routes, public health checks, allowed deployment origins, cross-origin write rejection, malformed credentials, custom-domain validation, and the ephemeral-storage indicator configuration.

The browser workflow used a disposable SQLite database and synthetic test credentials, not a deployed service or real user account. It exercised demo runs, five regression results, answer inspection, saved test reviews, report download, dataset navigation, prompt creation, run history, mobile layout, and reload persistence through a running Python server.

**Not yet verified:** a full Docker build (Docker is unavailable in the execution environment), GitHub Actions on the user's repository, and an actual Render deployment. A Docker build/startup check is included in `.github/workflows/ci.yml` for execution after upload. The service has not been published because GitHub and Render account connections were not available during preparation.

No actual Devara/Ollama model was invoked. The default Free Render Blueprint has temporary SQLite storage; the UI and hosting guide disclose the reset behavior. Durable storage is an optional paid configuration, not enabled by this update.

Detailed results: `hosting-tests.txt` and `hosted-browser-smoke.txt`.
