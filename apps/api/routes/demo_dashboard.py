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
    .teach-steps {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 8px;
    }
    .teach-steps li {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      border: 1px solid rgba(29, 26, 22, 0.08);
      background: rgba(29, 26, 22, 0.035);
      border-radius: 12px;
      padding: 10px 12px;
    }
    .step-state {
      font-family: Consolas, "Liberation Mono", monospace;
      font-size: 0.8rem;
      border-radius: 999px;
      padding: 3px 8px;
      background: rgba(29, 26, 22, 0.08);
      color: var(--muted);
      white-space: nowrap;
    }
    .step-state.observed, .step-state.ready { color: var(--success); }
    .step-state.missing { color: var(--danger); }
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
      <div class="card full">
        <h2>Human Recording v0.2</h2>
        <p>
          Controlled browser-side capture for the Fake ERP formula review flow only.
          Start a session here, open the Fake ERP sales orders page with a recording id,
          then finish, compile, and run the resulting skill.
        </p>
        <div class="toolbar">
          <button id="startHumanRecording" type="button">Start human recording</button>
          <button id="openHumanRecording" type="button">Open Fake ERP sales orders</button>
          <button id="finishHumanRecording" type="button">Finish recording</button>
          <button id="compileHumanRecording" type="button">Compile recording</button>
          <button id="runHumanRecording" type="button">Run compiled skill</button>
        </div>
        <p class="tiny">The capture mode only listens to the known Fake ERP selectors and keeps the recording id across navigation.</p>
        <pre id="humanStatus">No human recording started.</pre>
        <h3>Teach Mode v0.3</h3>
        <ol class="teach-steps" id="teachModeSteps">
          <li data-step-id="start_recording">Start recording <span class="step-state pending">pending</span></li>
          <li data-step-id="open_fake_erp">Open Fake ERP <span class="step-state pending">pending</span></li>
          <li data-step-id="order_search">Search order <span class="step-state pending">pending</span></li>
          <li data-step-id="open_order">Open order <span class="step-state pending">pending</span></li>
          <li data-step-id="formula_tab">Open formula tab <span class="step-state pending">pending</span></li>
          <li data-step-id="review_formula">Review formula <span class="step-state pending">pending</span></li>
          <li data-step-id="finish_recording">Finish recording <span class="step-state pending">pending</span></li>
          <li data-step-id="compile_skill">Compile skill <span class="step-state pending">pending</span></li>
          <li data-step-id="run_allow_block_proof">Run allow/block proof <span class="step-state pending">pending</span></li>
          <li hidden data-step-id="sales_orders_navigation">sales_orders_navigation <span class="step-state pending">pending</span></li>
        </ol>
        <p class="tiny" id="teachModeReadiness">Teach Mode readiness: not_ready</p>
        <h3>Recording Preview</h3>
        <p class="tiny">Shows ordered events, selectors captured, and compiler readiness before compilation.</p>
        <pre id="humanPreview">compiler readiness: not_ready
ordered events: none
selectors captured: none</pre>
        <pre id="humanResults">No compiled skill yet.</pre>
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
    const startHumanRecordingButton = document.getElementById("startHumanRecording");
    const openHumanRecordingButton = document.getElementById("openHumanRecording");
    const finishHumanRecordingButton = document.getElementById("finishHumanRecording");
    const compileHumanRecordingButton = document.getElementById("compileHumanRecording");
    const runHumanRecordingButton = document.getElementById("runHumanRecording");
    const humanStatus = document.getElementById("humanStatus");
    const humanPreview = document.getElementById("humanPreview");
    const humanResults = document.getElementById("humanResults");
    const teachModeReadiness = document.getElementById("teachModeReadiness");

    const humanState = {
      recordingId: null,
      skillId: null,
      versionId: null,
      fakeErpOpened: false,
      recordingFinished: false,
      proofRun: false,
    };

    const humanDefaults = {
      name: "Human Recorded Fake ERP Formula Review",
      description: "Controlled human recording from the demo surface.",
      erp_type: "fake",
      target_base_url: defaults.base_url,
      actor: { type: "user", id: "demo_user", display_name: "Demo User" },
    };

    const currentBaseUrl = () => baseUrlInput.value.trim() || defaults.base_url;

    const setHumanStatus = (value) => {
      humanStatus.textContent = value;
    };

    const setHumanResults = (value) => {
      humanResults.textContent = value;
    };

    const eventSummary = (event) => ({
      index: event.event_index,
      type: event.event_type,
      selector: event.selector,
      input_value: event.input_value,
      text: event.element_text,
      url: event.url,
    });

    const compilerReadiness = (events) => {
      const selectors = events.map((event) => event.selector).filter(Boolean);
      const hasNavigation = events.some((event) =>
        event.event_type === "navigate" && String(event.url || "").includes("/fake-erp/sales/orders")
      );
      const hasSearch = events.some((event) =>
        event.event_type === "fill" && event.selector === "[data-testid='order-search']"
      );
      const hasOpenOrder = selectors.some((selector) => selector.startsWith("[data-testid='open-order-"));
      const hasFormulaTab = selectors.includes("[data-testid='formula-tab']");
      const hasReviewFormula = selectors.includes("[data-testid='review-formula']");
      return hasNavigation && hasSearch && hasOpenOrder && hasFormulaTab && hasReviewFormula ? "ready" : "not_ready";
    };

    const renderRecordingPreview = (recording) => {
      const events = recording.events || [];
      const selectors = [...new Set(events.map((event) => event.selector).filter(Boolean))];
      humanPreview.textContent = jsonText({
        recording_id: recording.recording_id,
        status: recording.status,
        event_count: recording.event_count,
        "ordered events": events.map(eventSummary),
        "selectors captured": selectors,
        "compiler readiness": compilerReadiness(events),
      });
    };

    const setTeachStepState = (stepId, state) => {
      const step = document.querySelector(`[data-step-id="${stepId}"]`);
      if (!step) return;
      const badge = step.querySelector(".step-state");
      if (!badge) return;
      badge.textContent = state;
      badge.className = `step-state ${state}`;
    };

    const renderTeachMode = (readiness) => {
      const serverSteps = Object.fromEntries((readiness.steps || []).map((step) => [step.id, step.status]));
      setTeachStepState("start_recording", humanState.recordingId ? "observed" : "pending");
      setTeachStepState("open_fake_erp", humanState.fakeErpOpened ? "observed" : "pending");
      setTeachStepState("order_search", serverSteps.order_search || "pending");
      setTeachStepState("open_order", serverSteps.open_order || "pending");
      setTeachStepState("formula_tab", serverSteps.formula_tab || "pending");
      setTeachStepState("review_formula", serverSteps.review_formula || "pending");
      setTeachStepState("finish_recording", humanState.recordingFinished ? "observed" : "pending");
      setTeachStepState("compile_skill", readiness.readiness === "ready" ? "ready" : "pending");
      setTeachStepState("run_allow_block_proof", humanState.proofRun ? "observed" : "pending");
      setTeachStepState("sales_orders_navigation", serverSteps.sales_orders_navigation || "pending");
      teachModeReadiness.textContent = `Teach Mode readiness: ${readiness.readiness || "not_ready"}`;
    };

    const refreshTeachModeReadiness = async () => {
      if (!humanState.recordingId) {
        renderTeachMode({ readiness: "not_ready", steps: [] });
        return null;
      }

      const response = await fetch(`/v1/recordings/${humanState.recordingId}/readiness`);
      const body = await response.json();
      if (!response.ok) {
        teachModeReadiness.textContent = `Teach Mode readiness unavailable: ${body?.error?.message || "unknown error"}`;
        return null;
      }
      renderTeachMode(body);
      return body;
    };

    const refreshRecordingPreview = async () => {
      if (!humanState.recordingId) {
        humanPreview.textContent = "compiler readiness: not_ready\nordered events: none\nselectors captured: none";
        await refreshTeachModeReadiness();
        return;
      }

      const response = await fetch(`/v1/recordings/${humanState.recordingId}`);
      const body = await response.json();
      if (!response.ok) {
        humanPreview.textContent = `Preview unavailable: ${body?.error?.message || "unknown error"}`;
        return;
      }
      renderRecordingPreview(body);
      await refreshTeachModeReadiness();
    };

    const openFakeErpWithRecording = () => {
      if (!humanState.recordingId) {
        setHumanStatus("Start a human recording first.");
        return;
      }

      const url = new URL("/fake-erp/sales/orders", currentBaseUrl());
      url.searchParams.set("recording_id", humanState.recordingId);
      window.open(url.toString(), "_blank", "noopener,noreferrer");
      humanState.fakeErpOpened = true;
      renderTeachMode({ readiness: "not_ready", steps: [] });
      setHumanStatus(`Opened Fake ERP sales orders with recording_id=${humanState.recordingId}`);
    };

    const jsonText = (value) => JSON.stringify(value, null, 2);

    startHumanRecordingButton.addEventListener("click", async () => {
      startHumanRecordingButton.disabled = true;
      setHumanStatus("Starting human recording...");
      try {
        const response = await fetch("/v1/recordings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...humanDefaults,
            target_base_url: currentBaseUrl(),
          }),
        });

        const body = await response.json();
        if (!response.ok) {
          setHumanStatus(`Failed to start recording: ${body?.error?.message || "unknown error"}`);
          return;
        }

        humanState.recordingId = body.recording_id;
        humanState.skillId = null;
        humanState.versionId = null;
        humanState.fakeErpOpened = false;
        humanState.recordingFinished = false;
        humanState.proofRun = false;
        setHumanStatus(jsonText({
          recording_id: body.recording_id,
          name: body.name,
          status: body.status,
          target_base_url: body.target_base_url,
          instruction: "Open Fake ERP sales orders and perform the controlled flow.",
        }));
        await refreshRecordingPreview();
        setHumanResults("Recording started. Use the open button, then perform the controlled Fake ERP flow in the new tab.");
      } catch (error) {
        setHumanStatus(`Failed to start recording: ${String(error)}`);
      } finally {
        startHumanRecordingButton.disabled = false;
      }
    });

    openHumanRecordingButton.addEventListener("click", openFakeErpWithRecording);

    finishHumanRecordingButton.addEventListener("click", async () => {
      if (!humanState.recordingId) {
        setHumanStatus("Start a human recording first.");
        return;
      }

      finishHumanRecordingButton.disabled = true;
      setHumanStatus(`Finishing recording ${humanState.recordingId}...`);
      try {
        const response = await fetch(`/v1/recordings/${humanState.recordingId}/finish`, {
          method: "POST",
        });
        const body = await response.json();
        if (!response.ok) {
          setHumanStatus(`Failed to finish recording: ${body?.error?.message || "unknown error"}`);
          return;
        }

        setHumanStatus(jsonText(body));
        humanState.recordingFinished = true;
        await refreshRecordingPreview();
      } catch (error) {
        setHumanStatus(`Failed to finish recording: ${String(error)}`);
      } finally {
        finishHumanRecordingButton.disabled = false;
      }
    });

    compileHumanRecordingButton.addEventListener("click", async () => {
      if (!humanState.recordingId) {
        setHumanStatus("Start a human recording first.");
        return;
      }

      compileHumanRecordingButton.disabled = true;
      setHumanStatus(`Compiling recording ${humanState.recordingId}...`);
      try {
        const response = await fetch(`/v1/recordings/${humanState.recordingId}/compile-skill`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: humanDefaults.name,
            description: humanDefaults.description,
            runtime_type: "deterministic_browser",
          }),
        });

        const body = await response.json();
        if (!response.ok) {
          setHumanStatus(`Failed to compile recording: ${body?.error?.message || "unknown error"}`);
          return;
        }

        humanState.skillId = body.skill_id;
        humanState.versionId = body.version_id;
        setTeachStepState("compile_skill", "observed");
        setHumanStatus(jsonText({
          recording_id: body.recording_id,
          skill_id: body.skill_id,
          version_id: body.version_id,
          name: body.name,
          llm_required_for_repeated_runs: body.llm_required_for_repeated_runs,
        }));
      } catch (error) {
        setHumanStatus(`Failed to compile recording: ${String(error)}`);
      } finally {
        compileHumanRecordingButton.disabled = false;
      }
    });

    runHumanRecordingButton.addEventListener("click", async () => {
      if (!humanState.skillId) {
        setHumanStatus("Compile the human recording first.");
        return;
      }

      runHumanRecordingButton.disabled = true;
      setHumanResults("Running compiled skill...");
      try {
        const validResponse = await fetch(`/v1/skills/${humanState.skillId}/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ inputs: { order_reference: "SO-VALID" } }),
        });
        const validBody = await validResponse.json();

        const invalidResponse = await fetch(`/v1/skills/${humanState.skillId}/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ inputs: { order_reference: "SO-FORMULA-MISMATCH" } }),
        });
        const invalidBody = await invalidResponse.json();

        if (!validResponse.ok || !invalidResponse.ok) {
          setHumanResults(jsonText({
            valid_error: validBody,
            invalid_error: invalidBody,
          }));
          return;
        }

        setHumanResults(jsonText({
          recording_id: humanState.recordingId,
          skill_id: humanState.skillId,
          version_id: humanState.versionId,
          valid_decision: validBody.decision,
          invalid_decision: invalidBody.decision,
          invalid_issues_count: invalidBody.output?.issues?.length ?? 0,
          repeated_execution_token_cost: validBody.token_economics?.repeated_execution_token_cost,
        }));
        humanState.proofRun = true;
        setTeachStepState("run_allow_block_proof", "observed");
      } catch (error) {
        setHumanResults(`Failed to run compiled skill: ${String(error)}`);
      } finally {
        runHumanRecordingButton.disabled = false;
      }
    });

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
