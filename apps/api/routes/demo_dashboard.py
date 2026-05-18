from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["demo-dashboard"])


@router.get("/demo", response_class=HTMLResponse)
def demo_dashboard() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ERP Agent OS — Record-to-Skill MVP</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5efe6;
      --panel: #fffaf2;
      --ink: #1d1a16;
      --muted: #655c52;
      --accent: #8f4b1f;
      --accent-2: #275d63;
      --border: #dccdb9;
      --success: #186a3b;
      --danger: #9b2c2c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(143, 75, 31, 0.14), transparent 35%),
        radial-gradient(circle at bottom right, rgba(39, 93, 99, 0.12), transparent 32%),
        var(--bg);
    }
    main {
      max-width: 1080px;
      margin: 0 auto;
      padding: 40px 20px 64px;
    }
    .hero {
      display: grid;
      gap: 18px;
      grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
      align-items: start;
      margin-bottom: 28px;
    }
    .card {
      background: rgba(255, 250, 242, 0.9);
      border: 1px solid var(--border);
      border-radius: 20px;
      box-shadow: 0 16px 45px rgba(37, 27, 16, 0.08);
      padding: 22px;
    }
    h1, h2, h3 { margin: 0 0 12px; line-height: 1.1; }
    h1 { font-size: clamp(2.2rem, 4vw, 4.2rem); letter-spacing: -0.04em; }
    h2 { font-size: 1.35rem; }
    p { margin: 0 0 12px; color: var(--muted); line-height: 1.55; }
    .eyebrow { color: var(--accent-2); font-weight: 700; text-transform: uppercase; letter-spacing: 0.14em; font-size: 0.78rem; }
    .flow {
      display: grid;
      gap: 8px;
      margin-top: 12px;
      color: var(--muted);
      font-size: 0.98rem;
    }
    .flow span {
      padding: 8px 12px;
      background: rgba(39, 93, 99, 0.07);
      border-radius: 999px;
      border: 1px solid rgba(39, 93, 99, 0.12);
      width: fit-content;
    }
    .toolbar {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: end;
      margin-top: 14px;
    }
    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 0.92rem;
      min-width: min(100%, 380px);
    }
    input {
      width: 100%;
      border: 1px solid var(--border);
      background: #fff;
      border-radius: 12px;
      padding: 12px 14px;
      font: inherit;
      color: var(--ink);
    }
    button {
      border: 0;
      background: linear-gradient(135deg, var(--accent), #b46a32);
      color: white;
      border-radius: 999px;
      padding: 13px 18px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 14px 26px rgba(143, 75, 31, 0.24);
    }
    button:disabled { opacity: 0.65; cursor: progress; }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }
    pre, code {
      font-family: Consolas, "Liberation Mono", monospace;
    }
    pre {
      white-space: pre-wrap;
      margin: 0;
      background: rgba(29, 26, 22, 0.04);
      border: 1px solid rgba(29, 26, 22, 0.08);
      border-radius: 16px;
      padding: 16px;
      min-height: 72px;
    }
    .status {
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 999px;
      display: inline-block;
      margin-bottom: 8px;
      background: rgba(29, 26, 22, 0.06);
    }
    .ok { color: var(--success); }
    .bad { color: var(--danger); }
    .full { grid-column: 1 / -1; }
    .tiny { font-size: 0.9rem; color: var(--muted); }
    @media (max-width: 860px) {
      .hero, .grid { grid-template-columns: 1fr; }
      .full { grid-column: auto; }
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="card">
        <div class="eyebrow">ERP Agent OS</div>
        <h1>Record-to-Skill MVP</h1>
        <p>
          This demo surface turns the current API-only MVP into a simple operator view.
          It shows the full path from Fake ERP Web to browser recording, skill compilation,
          deterministic replay, ERPGuard formula validation, and token economics.
        </p>
        <div class="toolbar">
          <label>
            Base URL
            <input id="baseUrl" value="http://127.0.0.1:8000" />
          </label>
          <button id="runButton" type="button">Run full demo</button>
        </div>
        <p class="tiny" id="message">Click the button to run the current MVP end-to-end.</p>
      </div>
      <div class="card">
        <h2>Flow</h2>
        <div class="flow">
          <span>Fake ERP Web</span>
          <span>Browser Recorder</span>
          <span>Recording Session</span>
          <span>Recording-to-Skill Compiler</span>
          <span>Skill Registry</span>
          <span>Deterministic Skill Run</span>
          <span>ERPGuard Formula Guard</span>
          <span>token economics</span>
        </div>
      </div>
    </section>

    <section class="grid">
      <div class="card">
        <h2>Results</h2>
        <pre id="results">Waiting for a demo run.</pre>
      </div>
      <div class="card">
        <h2>Token Economics</h2>
        <pre id="tokens">Waiting for a demo run.</pre>
      </div>
      <div class="card">
        <h2>Proof</h2>
        <pre id="proof">Waiting for a demo run.</pre>
      </div>
      <div class="card">
        <h2>Known Good Evidence</h2>
        <pre id="evidence">docs/demo/full_record_to_skill_success_response.json</pre>
      </div>
      <div class="card full">
        <h2>Request</h2>
        <pre id="request">POST /v1/demo/full-record-to-skill-flow</pre>
      </div>
    </section>
  </main>

  <script>
    const defaults = {
      base_url: "http://127.0.0.1:8000",
      record_order_reference: "SO-FORMULA-MISMATCH",
      valid_order_reference: "SO-VALID",
      invalid_order_reference: "SO-FORMULA-MISMATCH",
      actor: { type: "user", id: "demo_user", display_name: "Demo User" },
    };

    const message = document.getElementById("message");
    const results = document.getElementById("results");
    const tokens = document.getElementById("tokens");
    const proof = document.getElementById("proof");
    const runButton = document.getElementById("runButton");
    const baseUrlInput = document.getElementById("baseUrl");

    runButton.addEventListener("click", async () => {
      runButton.disabled = true;
      message.textContent = "Running full demo...";
      results.textContent = "Running...";
      tokens.textContent = "Running...";
      proof.textContent = "Running...";

      try {
        const response = await fetch("/v1/demo/full-record-to-skill-flow", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...defaults,
            base_url: baseUrlInput.value.trim() || defaults.base_url,
          }),
        });

        const body = await response.json();
        if (!response.ok) {
          if (body?.error?.code === "browser_runtime_unavailable") {
            const chromiumMessage = "Chromium is not installed. Run python -m playwright install chromium.";
            message.textContent = chromiumMessage;
            results.textContent = JSON.stringify(body, null, 2);
            tokens.textContent = chromiumMessage;
            proof.textContent = chromiumMessage;
            return;
          }

          message.textContent = "Demo failed.";
          results.textContent = JSON.stringify(body, null, 2);
          tokens.textContent = "See error response above.";
          proof.textContent = "See error response above.";
          return;
        }

        message.textContent = "Demo completed successfully.";
        results.textContent = JSON.stringify({
          recording_id: body.recording.recording_id,
          recording_status: body.recording.status,
          recording_event_count: body.recording.event_count,
          skill_id: body.skill.skill_id,
          version_id: body.skill.version_id,
          skill_name: body.skill.name,
          llm_required_for_repeated_runs: body.skill.llm_required_for_repeated_runs,
          valid_decision: body.runs.valid.decision,
          invalid_decision: body.runs.invalid.decision,
          invalid_issues_count: body.runs.invalid.issues_count,
        }, null, 2);
        tokens.textContent = JSON.stringify(body.token_economics, null, 2);
        proof.textContent = JSON.stringify(body.proof, null, 2);
      } catch (error) {
        message.textContent = "Demo request could not be completed.";
        results.textContent = String(error);
        tokens.textContent = "Demo request could not be completed.";
        proof.textContent = "Demo request could not be completed.";
      } finally {
        runButton.disabled = false;
      }
    });
  </script>
</body>
</html>"""
