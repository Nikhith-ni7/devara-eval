# Start Devara Eval

**Want a live website?** Follow `HOSTING.md`: upload to GitHub, then deploy the included Blueprint on Render. GitHub Pages alone cannot run this Python backend.

1. Install Python 3.11 or newer if needed.
2. Open Terminal inside this extracted folder.
3. Run:

```bash
bash scripts/start.sh
```

4. Open http://127.0.0.1:8000 in your browser.
5. Click **Run demo comparison**.

The first launch installs Python dependencies and needs internet. The compiled React dashboard is included; you do not need Node.js just to use this download.

The demo is synthetic and needs no API key. To evaluate your real bot, follow `docs/DEVARA_INTEGRATION.md`. Read `README.md` for testing, development, and the project structure.
