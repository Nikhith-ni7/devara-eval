import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

async function api(path, options = {}) {
  const r = await fetch("/api" + path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const data = await r.json();
  if (!r.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail),
    );
  return data;
}
const pct = (n) => `${Math.round(n * 100)}%`;
const ms = (n) => `${Number(n).toFixed(1)} ms`;
const short = (id) => id?.slice(0, 8);
const Badge = ({ kind, children }) => (
  <span className={"badge " + kind}>{children || kind}</span>
);

function App() {
  const [tab, setTab] = useState("Comparisons"),
    [versions, setVersions] = useState([]),
    [runs, setRuns] = useState([]),
    [dataset, setDataset] = useState(null);
  const [baseline, setBaseline] = useState(""),
    [candidate, setCandidate] = useState(""),
    [comparison, setComparison] = useState(null);
  const [filter, setFilter] = useState("all"),
    [query, setQuery] = useState(""),
    [selected, setSelected] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const [launchVersion, setLaunchVersion] = useState("demo-baseline-v1"),
    [timeout, setTimeoutValue] = useState(30),
    [notice, setNotice] = useState("");
  const [runDetail, setRunDetail] = useState(null);
  const [deployment, setDeployment] = useState({hosted:false, ephemeral_storage:false});
  async function refresh() {
    const r = await api("/runs");
    setRuns(r);
    return r;
  }
  useEffect(() => {
    Promise.all([api("/versions"), api("/dataset"), refresh(), api("/config")])
      .then(([v, d, r, config]) => {
        setDeployment(config);
        setVersions(v);
        setDataset(d);
        const complete = r.filter((x) => x.status === "completed");
        if (complete.length >= 2) {
          setCandidate(complete[0].id);
          setBaseline(complete[1].id);
        }
      })
      .catch((e) => setError(e.message));
    const timer = setInterval(
      () => refresh().catch((e) => setError(e.message)),
      1500,
    );
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    let active = true;
    setComparison(null);
    setSelected(null);
    if (baseline && candidate)
      api(`/compare?baseline=${baseline}&candidate=${candidate}`)
        .then((c) => {
          if (active) setComparison(c);
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    return () => {
      active = false;
    };
  }, [baseline, candidate]);
  const completed = runs.filter((r) => r.status === "completed");
  const running = runs.filter((r) => ["queued", "running"].includes(r.status));
  async function launch(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const r = await api("/runs", {
        method: "POST",
        body: JSON.stringify({
          version_id: launchVersion,
          timeout_seconds: Number(timeout),
        }),
      });
      await refresh();
      setNotice(`Run ${short(r.id)} queued. Progress appears in Run history.`);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function demo() {
    setBusy(true);
    setError("");
    try {
      const a = await api("/runs", {
        method: "POST",
        body: JSON.stringify({
          version_id: "demo-baseline-v1",
          timeout_seconds: 0.25,
        }),
      });
      const b = await api("/runs", {
        method: "POST",
        body: JSON.stringify({
          version_id: "demo-candidate-v1",
          timeout_seconds: 0.25,
        }),
      });
      let done = false;
      for (let i = 0; i < 60; i++) {
        const r = await refresh();
        if (
          [a.id, b.id].every((id) =>
            r.some((x) => x.id === id && x.status === "completed"),
          )
        ) {
          done = true;
          break;
        }
        await new Promise((r) => setTimeout(r, 250));
      }
      if (!done)
        throw new Error(
          "Demo runs are still queued. Select them after they finish.",
        );
      setBaseline(a.id);
      setCandidate(b.id);
      setTab("Comparisons");
      setNotice(
        "Demo completed. Faults are deliberately injected; these are not Devara model results.",
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  const visible = (comparison?.rows || []).filter(
    (r) =>
      (filter === "all" ||
        (filter === "failed" ? !r.candidate.passed : r.change === filter)) &&
      `${r.question} ${r.case_id} ${r.category}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  return (
    <div className="layout">
      <aside>
        <a href="/" className="brand">
          <span className="brandmark">
            d<span>↗</span>
          </span>
          <div>
            devara<span>EVALUATION LAB</span>
          </div>
        </a>
        <div className="workspace">
          WORKSPACE
          <div>
            <span className="avatar">SA</span>
            <span>
              Sai’s engineering lab<small>{deployment.hosted ? "Hosted workspace" : "Local workspace"}</small>
            </span>
          </div>
        </div>
        <nav>
          {[
            "Comparisons",
            "Run history",
            "Test dataset",
            "Prompt versions",
          ].map((t, i) => (
            <button
              key={t}
              className={tab === t ? "active" : ""}
              onClick={() => {
                setTab(t);
                setSelected(null);
                setRunDetail(null);
              }}
            >
              <span>{["◫", "◷", "▤", "⌘"][i]}</span>
              {t}
              {t === "Test dataset" && (
                <small>{dataset?.cases.length || "—"}</small>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="live-dot" /> LOCAL-FIRST EVALUATION
          <p>Evidence for every change.</p>
          <small>Lexical checks + human review</small>
        </div>
        <a className="docs-link" href="/docs" target="_blank" rel="noreferrer">
          API documentation ↗
        </a>
      </aside>
      <main>
        <header>
          <div className="crumb">
            Workspace <span>/</span> Devara bot <span>/</span> {tab}
          </div>
          <span className="connection">
            <span className="live-dot" />
            {running.length
              ? `${running.length} runs in progress`
              : deployment.hosted ? "Hosted API" : "Local API"}
          </span>
        </header>
        <div className="content">
          <div className="heading">
            <div>
              <div className="eyebrow">AI QUALITY, MADE VISIBLE</div>
              <h1>
                {tab === "Comparisons" ? "Every change tells a story." : tab}
              </h1>
              <p>
                {tab === "Comparisons"
                  ? "Compare answers. Catch regressions. Ship with evidence."
                  : "A reproducible record of your assistant’s behavior."}
              </p>
            </div>
            <button className="primary" disabled={busy} onClick={demo}>
              {busy ? "Working…" : "▶ Run demo comparison"}
            </button>
          </div>
          {deployment.ephemeral_storage && <div className="notice" role="status">Hosted preview: history resets when the server restarts. Export important runs before leaving.</div>}
          {error && (
            <div role="alert" className="alert">
              {error}
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                ×
              </button>
            </div>
          )}
          {notice && (
            <div role="status" className="notice">
              {notice}
              <button aria-label="Dismiss notice" onClick={() => setNotice("")}>
                ×
              </button>
            </div>
          )}
          {tab === "Comparisons" && (
            <>
              <div className="compare-panel">
                <label>
                  <span>01 / BASELINE</span>
                  <select
                    aria-label="Baseline run"
                    value={baseline}
                    onChange={(e) => setBaseline(e.target.value)}
                  >
                    <option value="">Select a completed run</option>
                    {completed.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.version.id} · {short(r.id)}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="arrow">→</div>
                <label>
                  <span>02 / CANDIDATE</span>
                  <select
                    aria-label="Candidate run"
                    value={candidate}
                    onChange={(e) => setCandidate(e.target.value)}
                  >
                    <option value="">Select a completed run</option>
                    {completed.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.version.id} · {short(r.id)}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="dataset-tag">
                  DATASET<strong>{dataset?.version || "Loading…"}</strong>
                </div>
              </div>
              {comparison ? (
                <>
                  <div className="section-line">
                    <span>
                      <span className="live-dot" /> Comparison complete{" "}
                      <small>· {comparison.rows.length} matched cases</small>
                    </span>
                    {comparison.is_demo && (
                      <Badge kind="demo">SYNTHETIC DEMO</Badge>
                    )}
                    <button
                      className="text-button"
                      onClick={() => download(comparison)}
                    >
                      ↓ Export report
                    </button>
                  </div>
                  {comparison.settings_differ && (
                    <p className="alert">
                      Request deadlines differ between runs. Interpret timing
                      and failures with care.
                    </p>
                  )}
                  <div className="stats">
                    <Stat
                      label="CHECKS PASSED"
                      value={`${comparison.candidate_summary.passed} / ${comparison.rows.length}`}
                      detail={`Baseline: ${comparison.baseline_summary.passed} passed`}
                      kind="blue"
                    />
                    <Stat
                      label="IMPROVED"
                      value={comparison.counts.improved}
                      detail="Higher score or recovered response"
                      kind="green"
                    />
                    <Stat
                      label="REGRESSED"
                      value={comparison.counts.regressed}
                      detail="Lower score or new provider failure"
                      kind="red"
                    />
                    <Stat
                      label="MEDIAN RESPONSE"
                      value={ms(comparison.candidate_summary.median_ms)}
                      detail={`Baseline: ${ms(comparison.baseline_summary.median_ms)}`}
                      kind="purple"
                    />
                  </div>
                  <div className="results-head">
                    <div>
                      <h2>
                        Test results <span>{comparison.rows.length}</span>
                      </h2>
                      <p>Inspect the evidence behind each outcome.</p>
                    </div>
                    <input
                      aria-label="Search tests"
                      placeholder="Search questions or categories…"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                  </div>
                  <div className="tabs">
                    {[
                      ["all", "All tests"],
                      ["regressed", "Regressed"],
                      ["improved", "Improved"],
                      ["failed", "Candidate failed"],
                      ["unchanged", "Unchanged"],
                    ].map(([id, label]) => (
                      <button
                        key={id}
                        className={filter === id ? "selected" : ""}
                        onClick={() => setFilter(id)}
                      >
                        {label}
                        {id === "all"
                          ? ` ${comparison.rows.length}`
                          : id === "failed"
                            ? ` ${comparison.candidate_summary.failures}`
                            : ` ${comparison.counts[id]}`}
                      </button>
                    ))}
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>TEST CASE</th>
                          <th>BASELINE</th>
                          <th>CANDIDATE</th>
                          <th>CHANGE</th>
                          <th>LATENCY Δ</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {visible.map((row) => (
                          <tr
                            key={row.case_id}
                            onClick={() => setSelected(row)}
                          >
                            <td>
                              <small className="case-code">
                                {row.case_id.toUpperCase()}{" "}
                                <span>· {row.category}</span>
                              </small>
                              <strong>{row.question}</strong>
                            </td>
                            <td>
                              <Score value={row.baseline} />
                            </td>
                            <td>
                              <Score value={row.candidate} />
                            </td>
                            <td>
                              <Badge kind={row.change}>
                                {row.change === "regressed"
                                  ? "↘ "
                                  : row.change === "improved"
                                    ? "↗ "
                                    : "− "}
                                {row.change}
                              </Badge>
                            </td>
                            <td className="mono">
                              {row.latency_delta_ms > 0 ? "+" : ""}
                              {ms(row.latency_delta_ms)}
                            </td>
                            <td>
                              <button
                                className="inspect"
                                aria-label={`Inspect ${row.case_id}`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelected(row);
                                }}
                              >
                                ↗
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {!visible.length && (
                      <div className="empty small">
                        No tests match this filter.
                      </div>
                    )}
                  </div>
                  <p className="footnote">
                    Scores measure deterministic check completion, not answer
                    accuracy. Open-ended correctness requires human review.
                  </p>
                </>
              ) : (
                <div className="empty">
                  <div className="empty-icon">◫</div>
                  <h2>Your first comparison starts here.</h2>
                  <p>
                    Run the included 50-question demo to explore improvements,
                    <br />
                    injected failures, and the evidence behind each result.
                  </p>
                  <button className="primary" disabled={busy} onClick={demo}>
                    Run demo comparison →
                  </button>
                  <small>No API key or model download needed.</small>
                </div>
              )}
            </>
          )}
          {tab === "Run history" && (
            <>
              <form className="launch-card" onSubmit={launch}>
                <label>
                  Prompt / model version
                  <select
                    value={launchVersion}
                    onChange={(e) => setLaunchVersion(e.target.value)}
                  >
                    {versions.map((v) => (
                      <option key={v.id}>{v.id}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Deadline per question (seconds)
                  <input
                    type="number"
                    min="0.01"
                    max="120"
                    step="0.01"
                    required
                    value={timeout}
                    onChange={(e) => setTimeoutValue(e.target.value)}
                  />
                </label>
                <button className="primary" disabled={busy}>
                  Start evaluation →
                </button>
              </form>
              <p className="footnote">
                One run at a time, up to four queued. Ollama and Devara require
                a configured local service.
              </p>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>VERSION / RUN</th>
                      <th>STATUS</th>
                      <th>PROGRESS</th>
                      <th>CREATED</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {runs.map((r) => (
                      <tr key={r.id}>
                        <td>
                          <strong>{r.version.id}</strong>
                          <small className="mono">
                            {short(r.id)} {r.is_demo ? "· demo" : ""}
                          </small>
                        </td>
                        <td>
                          <Badge kind={r.status}>{r.status}</Badge>
                        </td>
                        <td>
                          {r.completed_cases} / {r.total_cases}
                        </td>
                        <td>{new Date(r.created_at).toLocaleString()}</td>
                        <td>
                          <button
                            onClick={() =>
                              api(`/runs/${r.id}`)
                                .then(setRunDetail)
                                .catch((e) => setError(e.message))
                            }
                          >
                            Inspect
                          </button>{" "}
                          <a href={`/api/runs/${r.id}/export`}>JSON ↓</a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!runs.length && (
                  <div className="empty small">
                    No runs yet. Start an evaluation above.
                  </div>
                )}
              </div>
              {runDetail && (
                <section className="panel">
                  <h2>
                    {runDetail.version.id} · {short(runDetail.id)}
                  </h2>
                  <p>
                    {runDetail.error ||
                      `${runDetail.summary.passed} passed checks; ${runDetail.summary.provider_failures} provider failures.`}
                  </p>
                  <pre>
                    {JSON.stringify(
                      {
                        settings: runDetail.version,
                        dataset_hash: runDetail.dataset_hash,
                        summary: runDetail.summary,
                      },
                      null,
                      2,
                    )}
                  </pre>
                  <p>{runDetail.reviews.length} human review records</p>
                </section>
              )}
            </>
          )}
          {tab === "Test dataset" && (
            <>
              <div className="info-panel">
                <strong>
                  {dataset?.version} · {dataset?.cases.length} cases · 9
                  categories
                </strong>
                <p>
                  Expected concepts use explicit lexical aliases. Code is
                  inspected as text and never executed. Edit the versioned JSON
                  file and restart the server to load a new dataset.
                </p>
              </div>
              {dataset?.cases.map((c) => (
                <details className="case-card" key={c.id}>
                  <summary>
                    <span className="mono">{c.id}</span>
                    <strong>{c.question}</strong>
                    <Badge kind="category">{c.category}</Badge>
                  </summary>
                  <div className="case-body">
                    <p>{c.facts.map((f) => f.label).join(" · ")}</p>
                    <p>
                      Minimum {c.min_words} words
                      {c.require_code ? " · Fenced code required" : ""}
                    </p>
                    <p>
                      <strong>Human review:</strong> {c.review_notes}
                    </p>
                    <pre>{JSON.stringify(c.facts, null, 2)}</pre>
                  </div>
                </details>
              ))}
            </>
          )}
          {tab === "Prompt versions" && (
            <>
              <VersionForm
                onSave={async (v) => {
                  try {
                    await api("/versions", {
                      method: "POST",
                      body: JSON.stringify(v),
                    });
                    setVersions(await api("/versions"));
                    setNotice(
                      "Immutable version saved. Start it from Run history.",
                    );
                  } catch (e) {
                    setError(e.message);
                    throw e;
                  }
                }}
              />
              {versions.map((v) => (
                <details key={v.id} className="case-card">
                  <summary>
                    <strong>{v.id}</strong>
                    <Badge kind="category">{v.provider}</Badge>
                    <span className="mono">{v.model}</span>
                  </summary>
                  <div className="case-body">
                    <p>{v.system_prompt}</p>
                    <small>
                      Temperature {v.temperature} · Seed {v.seed} ·{" "}
                      {v.provider === "demo"
                        ? `Fixture variant ${v.demo_variant}`
                        : "Real provider adapter"}
                    </small>
                  </div>
                </details>
              ))}
            </>
          )}
        </div>
        <footer>
          DEVARA EVAL <span>Built for questions worth checking.</span>
          <span>v1.1 · Evaluation lab</span>
        </footer>
      </main>
      {selected && (
        <Detail
          row={selected}
          runId={candidate}
          caseInfo={selected.case_definition}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
function Stat({ label, value, detail, kind }) {
  return (
    <div className={"stat " + kind}>
      <small>{label}</small>
      <strong>{value}</strong>
      <span>{detail}</span>
    </div>
  );
}
function Score({ value }) {
  return (
    <div className="score">
      <span>{pct(value.score)}</span>
      <div>
        <i style={{ width: pct(value.score) }} />
      </div>
      {value.status !== "ok" && (
        <small className="error-text">{value.status}</small>
      )}
    </div>
  );
}
function download(data) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = `comparison-${short(data.candidate_id)}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function VersionForm({ onSave }) {
  const [form, setForm] = useState({
      id: "",
      provider: "ollama",
      model: "qwen2.5-coder:7b",
      system_prompt:
        "You are Devara, a programming assistant. Answer accurately and include code when requested.",
      temperature: 0,
      seed: 42,
      demo_variant: "baseline",
    }),
    [saving, setSaving] = useState(false);
  function field(key, value) {
    setForm({ ...form, [key]: value });
  }
  return (
    <form
      className="panel version-form"
      onSubmit={async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
          await onSave(form);
          setForm({ ...form, id: "" });
        } catch {
        } finally {
          setSaving(false);
        }
      }}
    >
      <h2>Create a prompt version</h2>
      <p>Versions are immutable. Use a new ID for every change.</p>
      <div className="form-grid">
        <label>
          Version ID
          <input
            required
            pattern="[a-zA-Z0-9_-]{1,60}"
            placeholder="devara-prompt-v2"
            value={form.id}
            onChange={(e) => field("id", e.target.value)}
          />
        </label>
        <label>
          Provider
          <select
            aria-label="Provider"
            value={form.provider}
            onChange={(e) => field("provider", e.target.value)}
          >
            {["ollama", "devara", "demo"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <label>
          Model / deployment revision
          <input
            required
            value={form.model}
            onChange={(e) => field("model", e.target.value)}
          />
        </label>
        <label>
          Temperature
          <input
            type="number"
            min="0"
            max="2"
            step="0.1"
            value={form.temperature}
            onChange={(e) => field("temperature", Number(e.target.value))}
          />
        </label>
      </div>
      <label>
        System prompt
        <textarea
          required
          rows="3"
          value={form.system_prompt}
          onChange={(e) => field("system_prompt", e.target.value)}
        />
      </label>
      <button disabled={saving} className="primary">
        {saving ? "Saving…" : "Save version"}
      </button>
    </form>
  );
}
function Detail({ row, runId, caseInfo, onClose }) {
  const [message, setMessage] = useState(""),
    [saving, setSaving] = useState(false);
  useEffect(() => {
    const h = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [onClose]);
  async function review(e) {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    const d = new FormData(e.target);
    try {
      await api(`/runs/${runId}/reviews/${row.case_id}`, {
        method: "POST",
        body: JSON.stringify({
          reviewer: d.get("reviewer"),
          correctness: Number(d.get("correctness")),
          completeness: Number(d.get("completeness")),
          clarity: Number(d.get("clarity")),
          notes: d.get("notes"),
        }),
      });
      setMessage("Review saved to the candidate run.");
    } catch (e) {
      setMessage(e.message);
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="overlay" onClick={onClose}>
      <section
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="detail-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          autoFocus
          className="close"
          onClick={onClose}
          aria-label="Close test details"
        >
          ×
        </button>
        <div className="eyebrow">
          {row.case_id} · {row.category}
        </div>
        <h2 id="detail-title">{row.question}</h2>
        <Badge kind={row.change} />
        <div className="answers">
          {["baseline", "candidate"].map((side) => (
            <article key={side}>
              <h3>
                {side} <span>{pct(row[side].score)}</span>
              </h3>
              <small>
                {ms(row[side].latency_ms)} · {row[side].status}
              </small>
              <pre>{row[side].answer || row[side].error || "(empty)"}</pre>
              <ul className="checks">
                {row[side].checks.map((c) => (
                  <li key={c.name} className={c.passed ? "pass" : "fail"}>
                    {c.passed ? "✓" : "×"} {c.name}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
        <form onSubmit={review} className="review">
          <h3>Human review · Candidate</h3>
          <p>{caseInfo?.review_notes}</p>
          <p className="footnote">
            0 = incorrect / missing / unclear · 1 = partial · 2 = correct /
            complete / clear. Lexical scores remain unchanged.
          </p>
          <div className="form-grid">
            {["correctness", "completeness", "clarity"].map((k) => (
              <label key={k}>
                {k}
                <select name={k} defaultValue="" required>
                  <option value="" disabled>
                    Select…
                  </option>
                  <option value="0">0</option>
                  <option value="1">1</option>
                  <option value="2">2</option>
                </select>
              </label>
            ))}
          </div>
          <label>
            Reviewer
            <input
              name="reviewer"
              required
              maxLength="100"
              placeholder="Your name"
            />
          </label>
          <label>
            Evidence / rationale
            <textarea
              name="notes"
              required
              maxLength="3000"
              rows="3"
              placeholder="Explain any factual error, missing edge case, or misleading explanation."
            />
          </label>
          <button className="primary" disabled={saving}>
            Save human review
          </button>
          <p role="status">{message}</p>
        </form>
      </section>
    </div>
  );
}
createRoot(document.getElementById("root")).render(<App />);
