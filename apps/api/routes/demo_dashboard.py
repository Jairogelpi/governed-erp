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
    .analysis-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
      margin: 10px 0 14px;
    }
    .analysis-card {
      border: 1px solid rgba(29, 26, 22, 0.1);
      border-radius: 16px;
      background: rgba(39, 93, 99, 0.05);
      padding: 14px;
      display: grid;
      gap: 10px;
    }
    .analysis-card h4 {
      margin: 0;
      font-size: 1.02rem;
    }
    .analysis-card .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      color: var(--muted);
      font-size: 0.82rem;
    }
    .analysis-pill {
      padding: 3px 8px;
      border-radius: 999px;
      background: rgba(143, 75, 31, 0.08);
      border: 1px solid rgba(143, 75, 31, 0.12);
    }
    .analysis-card button {
      justify-self: start;
      padding: 10px 14px;
    }
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
        <h3>Skill Inspector v0.4</h3>
        <p class="tiny">Inspect inputs, guards, workflow steps, and safety summary before trusting repeated runs.</p>
        <pre id="skillInspector">No inspected skill yet.</pre>
        <h3>Run History / Audit Timeline v0.5</h3>
        <p class="tiny">Shows the latest executions of the compiled skill and a step-by-step audit timeline.</p>
        <pre id="runHistory">No run history yet.</pre>
        <pre id="runTimeline">No audit timeline yet.</pre>
        <h3>Approval Gate / Safe Action Plan v0.6</h3>
        <p class="tiny">Preview the critical confirm_sales_order action and verify the approval gate before any real ERP write.</p>
        <div class="toolbar">
          <button id="planApprovalGate" type="button">Generate safe action plan</button>
        </div>
        <pre id="approvalGatePlan">No approval plan yet.</pre>
        <h3>Approval Decision Simulation v0.7</h3>
        <p class="tiny">Simulate approve or reject against the safe plan without executing confirm_sales_order.</p>
        <div class="toolbar">
          <button id="simulateApproveGate" type="button">Simulate approve for SO-VALID</button>
          <button id="simulateRejectGate" type="button">Simulate reject for SO-FORMULA-MISMATCH</button>
        </div>
        <pre id="approvalDecisionSimulation">No approval decision simulated yet.</pre>
      </div>
      <div class="card full">
        <h2>Release Candidate v0.12.0-rc1 — Operator Demo Pack</h2>
        <p>
          Sprint 12 — Packaging checkpoint. Seed demo data, check release readiness, run operator smoke test,
          and inspect safety boundaries. No new ERP capabilities. All write flags off by default.
          ALLOW_GENERIC_REAL_ODOO_WRITES=false. ALLOW_R3_R4_REAL_WRITES=false always.
        </p>
        <div class="toolbar">
          <button id="rcHealth" type="button">Release health</button>
          <button id="rcReadiness" type="button">Readiness report</button>
          <button id="rcDemoSeed" type="button">Seed demo data</button>
          <button id="rcSmoke" type="button">Run operator smoke test</button>
          <button id="rcSafetyBoundaries" type="button">Safety boundaries</button>
        </div>
        <p class="tiny" id="rcMessage">Check release health and readiness before seeding demo data or running the smoke test.</p>
        <pre id="rc-health-output">No health check yet.</pre>
        <pre id="rc-readiness-output">No readiness report yet.</pre>
        <pre id="rc-seed-output">No demo seed yet.</pre>
        <pre id="rc-smoke-output">No smoke test yet.</pre>
        <pre id="rc-safety-output">No safety boundaries yet.</pre>
        <p class="tiny">
          Sprint chain: 13 sprints (1 → 12) implemented and passing.
          Safety: <code>can_execute_real_writes=false</code> /
          <code>ALLOW_GENERIC_REAL_ODOO_WRITES=false</code> /
          <code>ALLOW_R3_R4_REAL_WRITES=false</code>
        </p>
      </div>
      <div class="card full">
        <h2>R2 Pilot Evidence Review, Rollback Rehearsal &amp; Production Readiness</h2>
        <p>
          Sprint 11 — Make the R2 pilot operationally defensible. Review evidence (pre/post snapshot delta),
          rehearse rollback (dry-run only, no real execution), generate an audit-grade execution report,
          measure residual risk, and evaluate the promotion gate. Blocked if any check fails.
          No new writes. ALLOW_GENERIC_REAL_ODOO_WRITES=false. ALLOW_R3_R4_REAL_WRITES=false always.
        </p>
        <div class="toolbar">
          <label>
            Run ID
            <input id="r2rRunId" placeholder="r2run_..." />
          </label>
          <button id="r2rEvidenceReview" type="button">Evidence review</button>
          <button id="r2rRollbackRehearsal" type="button">Rollback rehearsal (dry-run)</button>
          <button id="r2rExecutionReport" type="button">Execution report</button>
          <button id="r2rPromotionGate" type="button">Evaluate promotion gate</button>
        </div>
        <p class="tiny" id="r2rMessage">Enter an R2 run ID (from Sprint 10B) to review evidence, rehearse rollback, and check promotion readiness.</p>
        <pre id="r2r-review-output">No evidence review yet.</pre>
        <pre id="r2r-rehearsal-output">No rollback rehearsal yet.</pre>
        <pre id="r2r-report-output">No execution report yet.</pre>
        <pre id="r2r-gate-output">No promotion gate yet.</pre>
        <p class="tiny">
          Promotion gate checks: evidence review done, no drift, rollback rehearsal passed,
          execution report generated, residual risk ≤ 30. Blocked if any check fails.
          Real rollback never auto-executed — human operator confirms first.
        </p>
      </div>
      <div class="card full">
        <h2>R2 Controlled Write Pilot — res.partner.write (staging only)</h2>
        <p>
          Sprint 10B — First R2 reversible write candidate. Only <code>res.partner.write</code> on
          allowed fields (<code>comment</code>, <code>website</code>). Staging/demo environment only.
          Requires double approval (2 distinct approvers), Sprint 7 certification, pre/post snapshots,
          idempotency, and a stored rollback plan. Feature flag: ALLOW_R2_REAL_WRITE_PILOT=false by default.
          ALLOW_GENERIC_REAL_ODOO_WRITES=false. ALLOW_R3_R4_REAL_WRITES=false always.
        </p>
        <div class="toolbar">
          <label>
            Skill ID
            <input id="r2SkillId" placeholder="skill_..." />
          </label>
          <button id="r2CreateRequest" type="button">Create R2 request</button>
          <button id="r2CheckPolicy" type="button">Check R2 policy</button>
          <button id="r2Execute" type="button">Execute R2 (blocked by default)</button>
          <button id="r2GetRun" type="button">Get run result</button>
          <button id="r2GetEvidence" type="button">Get evidence &amp; rollback</button>
          <button id="r2History" type="button">Show R2 history</button>
        </div>
        <p class="tiny" id="r2Message">Enter a skill id with Sprint 7 certification. Staging only. Blocked by default.</p>
        <pre id="r2-request-output">No R2 request yet.</pre>
        <pre id="r2-policy-output">No R2 policy check yet.</pre>
        <pre id="r2-run-output">No R2 run yet.</pre>
        <pre id="r2-evidence-output">No R2 evidence yet.</pre>
        <pre id="r2-history-output">No R2 history yet.</pre>
        <p class="tiny">
          Whitelisted: <code>res.partner.write</code> on <code>comment</code>, <code>website</code> only.
          Environments: <code>staging</code> / <code>demo</code> only.
          Blocked: <code>sale.order.action_confirm</code> / <code>account.move.action_post</code> /
          any R3/R4 / any generic write.
        </p>
      </div>
      <div class="card full">
        <h2>ERP Agent OS — End-to-End Operator Flow</h2>
        <p>
          Sprint 10A — Guided operator flow. Move through the full ERP Agent OS path without manually copying IDs.
          Each step advances automatically: tenant creation, connection selection, business analysis, skill compilation,
          approval, activation, live read, and write readiness. No new ERP writes. ALLOW_GENERIC_REAL_ODOO_WRITES=false.
        </p>
        <div class="toolbar">
          <button id="ofCreateSession" type="button">Create operator session</button>
          <label>
            Connection ID
            <input id="ofConnectionId" placeholder="conn_..." />
          </label>
          <button id="ofSelectConnection" type="button">Select connection</button>
          <button id="ofRunNext" type="button">Run next step</button>
          <button id="ofRunSafeReadonly" type="button">Run full safe read-only path</button>
          <button id="ofTimeline" type="button">View timeline</button>
          <button id="ofSummary" type="button">View summary</button>
        </div>
        <p class="tiny" id="ofMessage">Create a session first, then optionally select an Odoo connection and run the flow.</p>
        <pre id="of-session-output">No operator session yet.</pre>
        <pre id="of-run-output">No step run yet.</pre>
        <pre id="of-timeline-output">No timeline yet.</pre>
        <pre id="of-summary-output">No summary yet.</pre>
        <p class="tiny">
          Safety: <code>can_execute_real_writes=false</code> /
          <code>ALLOW_GENERIC_REAL_ODOO_WRITES=false</code> /
          <code>ALLOW_R3_R4_REAL_WRITES=false</code> /
          <code>approved_for_real_execution=false</code>
        </p>
      </div>
      <div class="card full">
        <h2>Production Safety &amp; Tenant Controls</h2>
        <p>
          Sprint 9 — Platform hardening before any new write risk. Tenant lifecycle, per-tenant kill switches,
          secret redaction, audit export, RBAC policy evaluation, and runtime safety dashboard.
          No new ERP writes added. ALLOW_GENERIC_REAL_ODOO_WRITES=false. ALLOW_R3_R4_REAL_WRITES=false always.
        </p>
        <div class="toolbar">
          <label>
            Tenant name
            <input id="psaTenantName" value="Demo Tenant" />
          </label>
          <button id="psaCreateTenant" type="button">Create tenant</button>
          <button id="psaGetSafetySummary" type="button">Get safety summary</button>
          <button id="psaActivateKillSwitch" type="button">Activate kill switch</button>
          <button id="psaDeactivateKillSwitch" type="button">Deactivate kill switch</button>
          <button id="psaGenerateAuditExport" type="button">Generate audit export</button>
          <button id="psaEvaluatePolicy" type="button">Evaluate operator policy</button>
          <button id="psaGetRuntimeSafety" type="button">Get runtime safety</button>
        </div>
        <p class="tiny" id="psaMessage">Create a tenant first, then test kill switches, audit export, and policy evaluation.</p>
        <pre id="psa-tenant-output">No tenant yet.</pre>
        <pre id="psa-summary-output">No safety summary yet.</pre>
        <pre id="psa-kill-switch-output">No kill switch event yet.</pre>
        <pre id="psa-audit-export-output">No audit export yet.</pre>
        <pre id="psa-policy-output">No policy evaluation yet.</pre>
        <pre id="psa-runtime-output">No runtime safety yet.</pre>
        <p class="tiny">
          Kill switches: <code>global_kill_switch</code> / <code>runtime_execution_kill_switch</code> /
          <code>write_pilot_kill_switch</code>. Secret redaction enforced. Audit export enabled.
          ALLOW_GENERIC_REAL_ODOO_WRITES=false. ALLOW_R3_R4_REAL_WRITES=false.
        </p>
      </div>
      <div class="card full">
        <h2>First Real Write Pilot — mail.message.create</h2>
        <p>
          Sprint 8 — Ultra-limited real Odoo write pilot. Only mail.message.create allowed. R1 risk only.
          Feature flag: ALLOW_R1_REAL_WRITE_PILOT=false by default (pilot is blocked unless explicitly enabled).
          ALLOW_GENERIC_REAL_ODOO_WRITES=false. ALLOW_R3_R4_REAL_WRITES=false always.
          Requires Sprint 7 write readiness certification + double human approval.
        </p>
        <div class="toolbar">
          <label>
            Skill ID
            <input id="wpSkillId" placeholder="skill_..." />
          </label>
          <button id="wpCreateRequest" type="button">Create pilot request</button>
          <button id="wpCheckPolicy" type="button">Check pilot policy</button>
          <button id="wpExecute" type="button">Execute pilot (blocked by default)</button>
          <button id="wpGetRun" type="button">Get run result</button>
          <button id="wpGetEvidence" type="button">Get pilot evidence</button>
          <button id="wpHistory" type="button">Show pilot history</button>
        </div>
        <p class="tiny" id="wpMessage">Enter an approved skill id (with Sprint 7 certification) to test the write pilot. Blocked by default.</p>
        <pre id="wp-request-output">No pilot request yet.</pre>
        <pre id="wp-policy-output">No policy check yet.</pre>
        <pre id="wp-run-output">No pilot run yet.</pre>
        <pre id="wp-evidence-output">No pilot evidence yet.</pre>
        <pre id="wp-history-output">No pilot history yet.</pre>
        <p class="tiny">
          Whitelisted: <code>mail.message.create</code> only.
          Blocked: <code>sale.order.action_confirm</code> / <code>stock.picking.button_validate</code> /
          <code>account.move.action_post</code> / <code>mrp.production.button_mark_done</code> /
          any generic <code>create/write/unlink/copy/action_*/button_*</code>.
        </p>
      </div>
      <div class="card full">
        <h2>Write Capability Readiness &amp; Risk Certification</h2>
        <p>
          Sprint 7 — Static analysis of write candidates for approved compiled skills.
          No real Odoo writes executed. Certifies IF a skill could become a write candidate in a future sprint.
          ALLOW_REAL_ODOO_WRITES=false. can_execute_real_writes=false. approved_for_real_execution=false always.
        </p>
        <div class="toolbar">
          <label>
            Skill ID
            <input id="wrSkillId" placeholder="skill_..." />
          </label>
          <button id="wrRunAssessment" type="button">Run write readiness assessment</button>
          <button id="wrGetSummary" type="button">Get readiness summary</button>
          <button id="wrGenerateImpact" type="button">Generate impact preview</button>
          <button id="wrDraftRollback" type="button">Draft rollback plan</button>
          <button id="wrCertify" type="button">Certify write readiness</button>
        </div>
        <p class="tiny" id="wrMessage">Enter an approved compiled skill id to run write readiness analysis. No Odoo writes executed.</p>
        <pre id="wr-assessment-output">No assessment yet.</pre>
        <pre id="wr-summary-output">No summary yet.</pre>
        <pre id="wr-impact-output">No impact preview yet.</pre>
        <pre id="wr-rollback-output">No rollback plan yet.</pre>
        <pre id="wr-certification-output">No certification yet.</pre>
        <p class="tiny">
          Security invariants: <code>can_execute_real_writes=false</code> /
          <code>real_erp_writes_enabled=false</code> /
          <code>approved_for_real_execution=false</code> /
          <code>ALLOW_REAL_ODOO_WRITES=false</code>
        </p>
      </div>
      <div class="card full">
        <h2>Controlled Real Read Execution &amp; Live Evidence</h2>
        <p>
          Sprint 6 — Real read-only Odoo execution for approved compiled skills.
          ALLOW_REAL_ODOO_READS=true. ALLOW_REAL_ODOO_WRITES=false.
          Reads real data from Odoo; any write attempt is blocked with evidence.
        </p>
        <div class="toolbar">
          <label>
            Skill ID
            <input id="lrSkillId" placeholder="skill_..." />
          </label>
          <button id="lrCheckContext" type="button">Check connection context</button>
          <button id="lrCheckPolicy" type="button">Check live read policy</button>
          <button id="lrCreateRequest" type="button">Create live read request</button>
          <button id="lrRunExecution" type="button">Run live read</button>
          <button id="lrGetEvidence" type="button">Get live evidence</button>
        </div>
        <p class="tiny" id="lrMessage">Enter an approved compiled skill id (from Sprint 4) to execute a controlled real read.</p>
        <pre id="lrConnectionContext">No connection context yet.</pre>
        <pre id="lrPolicyOutput">No policy check yet.</pre>
        <pre id="lrRequestOutput">No live read request yet.</pre>
        <pre id="lrRunOutput">No live read run yet.</pre>
        <pre id="lrEvidenceOutput">No live evidence yet.</pre>
      </div>
      <div class="card full">
        <h2>Limited Approved Execution Sandbox</h2>
        <p>
          Sprint 5 — Dry-run execution of approved compiled skills. ALLOW_REAL_ODOO_WRITES=false.
          All attempted Odoo writes are blocked and stored as evidence. No real ERP writes ever happen.
        </p>
        <div class="toolbar">
          <label>
            Skill ID
            <input id="sandboxSkillId" placeholder="skill_..." />
          </label>
          <button id="checkExecutionPolicy" type="button">Check execution policy</button>
          <button id="createExecutionRequest" type="button">Create execution request</button>
          <button id="runExecution" type="button">Run (dry-run sandbox)</button>
          <button id="getExecutionTimeline" type="button">Get timeline</button>
          <button id="getBlockedWrites" type="button">List blocked writes</button>
        </div>
        <p class="tiny" id="sandboxMessage">Enter an approved compiled skill id (from Sprint 4) to execute in the sandbox.</p>
        <pre id="executionPolicyOutput">No policy check yet.</pre>
        <pre id="executionRequestOutput">No execution request yet.</pre>
        <pre id="executionRunOutput">No execution run yet.</pre>
        <pre id="executionTimelineOutput">No timeline yet.</pre>
        <pre id="blockedWritesOutput">No blocked writes yet.</pre>
      </div>
      <div class="card full">
        <h2>Skill Approval &amp; Activation Gates</h2>
        <p>
          Sprint 4 — Human approval workflow and activation gate for compiled dry-run skills.
          No real Odoo writes are enabled at any step. Approval only authorizes governance state.
        </p>
        <div class="toolbar">
          <label>
            Skill ID
            <input id="approvalSkillId" placeholder="skill_..." />
          </label>
          <label>
            Requester name
            <input id="approvalRequesterName" value="Demo Operator" />
          </label>
          <label>
            Approver name
            <input id="approvalApproverName" value="Demo Approver" />
          </label>
          <button id="submitApprovalRequest" type="button">Submit approval request</button>
          <button id="approveSkill" type="button">Approve (dry-run only)</button>
          <button id="rejectSkill" type="button">Reject</button>
          <button id="runActivationGate" type="button">Run activation gate</button>
          <button id="getGovernanceSummary" type="button">Governance summary</button>
        </div>
        <p class="tiny" id="approvalMessage">Enter a compiled skill id or run Sprint 3 compile first.</p>
        <pre id="approvalRequestOutput">No approval request yet.</pre>
        <pre id="approvalDecisionOutput">No approval decision yet.</pre>
        <pre id="activationGateOutput">No activation gate yet.</pre>
        <pre id="governanceSummaryOutput">No governance summary yet.</pre>
      </div>
      <div class="card full">
        <h2>Safe Agent Builder</h2>
        <p>
          This builder creates reviewed drafts only. It does not execute free-form agents or enable new ERP writes.
          Build from connector/template pieces, then send the draft through review / compile / approval.
        </p>
        <div class="toolbar">
          <label>
            Builder Template ID
            <input id="agentBuilderTemplateId" value="odoo_formula_preflight" />
          </label>
          <label>
            Builder Connector ID
            <input id="agentBuilderConnectorId" value="odoo" />
          </label>
          <label>
            Builder Connection ID
            <input id="agentBuilderConnectionId" placeholder="conn_..." />
          </label>
          <button id="createAgentBuilderSession" type="button">Create builder session</button>
          <button id="loadAgentBuilderStepLibrary" type="button">Load step library</button>
          <button id="configureAgentBuilder" type="button">Configure safe workflow</button>
          <button id="previewAgentBuilder" type="button">Preview execution plan</button>
          <button id="saveAgentBuilderDraft" type="button">Save as automation draft</button>
        </div>
        <p class="tiny">Allowed steps only. Mandatory guards: no_generic_writes, no_r3_r4_writes, no_raw_tool_execution, requires_human_review.</p>
        <pre id="agentBuilderSessionOutput">No builder session yet.</pre>
        <pre id="agentBuilderStepLibraryOutput">No step library loaded yet.</pre>
        <pre id="agentBuilderPreviewOutput">No workflow preview yet.</pre>
        <pre id="agentBuilderDraftOutput">No builder draft saved yet.</pre>
      </div>
      <div class="card full">
        <h2>Skill Marketplace / Connector Catalog</h2>
        <p>
          Sprint 15 — Browse controlled connectors and predefined automation templates.
          Templates install only as draft, then must go through review, validation, compile, and approval.
          No MCP execution gateway. No new ERP writes.
        </p>
        <div class="toolbar">
          <label>
            Marketplace Connection ID
            <input id="marketplaceConnectionId" placeholder="conn_..." />
          </label>
          <label>
            Template ID
            <input id="marketplaceTemplateId" value="odoo_formula_preflight" />
          </label>
          <button id="loadMarketplaceConnectors" type="button">Load connectors</button>
          <button id="loadMarketplaceTemplates" type="button">Load skill templates</button>
          <button id="checkMarketplaceRequirements" type="button">Check requirements</button>
          <button id="installMarketplaceDraft" type="button">Install as draft</button>
          <button id="loadMarketplaceInstalled" type="button">Installed drafts</button>
        </div>
        <p class="tiny">Connector, Skill template, Risk level, Required guards, Required connection, Required permissions, Safety summary, Compile later.</p>
        <pre id="marketplaceConnectorOutput">No connector catalog loaded yet.</pre>
        <pre id="marketplaceTemplateOutput">No skill template catalog loaded yet.</pre>
        <pre id="marketplaceRequirementsOutput">No requirements check yet.</pre>
        <pre id="marketplaceInstallOutput">No marketplace draft installed yet.</pre>
      </div>
      <div class="card full">
        <h2>Connector Credential Vault</h2>
        <p>
          Sprint 17 — Prepare connector authorization without enabling providers.
          No real OAuth flow. No external connector API calls. Secrets are redacted before any response or audit view.
        </p>
        <div class="toolbar">
          <label>
            Connector ID
            <input id="connectorAuthConnectorId" value="gmail" />
          </label>
          <label>
            Scope
            <input id="connectorAuthScope" value="gmail.readonly" />
          </label>
          <button id="loadConnectorScopes" type="button">Load scopes</button>
          <button id="createConnectorAuthProfile" type="button">Create auth profile</button>
          <button id="testConnectorAuthProfile" type="button">Simulate test</button>
          <button id="rotateConnectorAuthProfile" type="button">Rotate</button>
          <button id="revokeConnectorAuthProfile" type="button">Revoke</button>
          <button id="loadConnectorAuthAudit" type="button">Audit</button>
        </div>
        <p class="tiny">Credential Vault, Connector Auth Profile, OAuth Readiness Placeholder, Scope Registry, Secret Redaction, Connection Test Simulation, Revoke / Rotate, Audit Trail.</p>
        <pre id="connectorScopesOutput">No connector scopes loaded yet.</pre>
        <pre id="connectorAuthProfileOutput">No connector auth profile created yet.</pre>
        <pre id="connectorAuthTestOutput">No simulated connection test yet.</pre>
        <pre id="connectorAuthAuditOutput">No connector credential audit loaded yet.</pre>
      </div>

      <!-- Sprint 18 — External Connector Read-Only Pilot -->
      <div class="card full">
        <h2>External Connector Read-Only Pilot</h2>
        <p>
          Sprint 18 — First real external connector in fixture mode.
          Google Calendar read-only: policy check → redacted read → evidence → business signals.
          No events created, no emails sent, no PII exposed.
        </p>

        <label>Auth Profile ID (from Connector Vault above):</label>
        <input id="extConnProfileId" placeholder="auth_profile_..." style="width:340px" />

        <div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
          <button id="extConnPolicy">Get Policy</button>
          <button id="extConnTestReadiness">Test Readiness</button>
          <button id="extConnReadCalendars">Read Calendars</button>
          <button id="extConnReadEvents">Read Upcoming Events</button>
          <button id="extConnLoadEvidence">Load Evidence</button>
          <button id="extConnLoadSignals">Load Signals</button>
          <button id="extConnLoadAudit">Load Audit</button>
        </div>

        <pre id="extConnPolicyOutput">Policy not loaded yet.</pre>
        <pre id="extConnReadinessOutput">Readiness not tested yet.</pre>
        <pre id="extConnCalendarsOutput">Calendars not loaded yet.</pre>
        <pre id="extConnEventsOutput">Events not loaded yet.</pre>
        <pre id="extConnEvidenceOutput">Evidence not loaded yet.</pre>
        <pre id="extConnSignalsOutput">Signals not loaded yet.</pre>
        <pre id="extConnAuditOutput">Audit not loaded yet.</pre>
      </div>

      <!-- Sprint 19 — Real OAuth Consent Flow for Google Calendar Read-Only -->
      <div class="card full">
        <h2>Google Calendar OAuth Authorization</h2>
        <p>
          Sprint 19 — Real OAuth 2.0 consent flow for Google Calendar read-only.
          Placeholder mode when no Google credentials are set.
          Scope: <code>calendar.readonly</code> only. Tokens never exposed in UI or API.
        </p>

        <label>Auth Profile ID:</label>
        <input id="oauthProfileId" placeholder="auth_profile_..." style="width:340px" />
        <label style="margin-left:12px">Redirect URI (optional):</label>
        <input id="oauthRedirectUri" placeholder="http://localhost:8000/v1/oauth/google-calendar/callback" style="width:420px" />

        <div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
          <button id="oauthAuthorize">1. Get Authorization URL</button>
          <button id="oauthStatus">Check Auth Status</button>
          <button id="oauthVerifyScope">Verify Scope</button>
          <button id="oauthRevoke">Revoke Token</button>
        </div>

        <p style="font-size:0.85em; color:#666; margin-top:8px;">
          After getting the URL, open it in a browser (real mode) or use the
          <strong>Simulate Callback</strong> button to test the placeholder exchange.
        </p>

        <div style="margin-top:8px; display:flex; gap:8px; flex-wrap:wrap;">
          <label>State token (from step 1):</label>
          <input id="oauthStateToken" placeholder="state token from authorize response" style="width:340px" />
          <button id="oauthSimulateCallback">Simulate Callback (placeholder code)</button>
        </div>

        <pre id="oauthAuthorizeOutput">Authorization URL not generated yet.</pre>
        <pre id="oauthCallbackOutput">Callback not executed yet.</pre>
        <pre id="oauthStatusOutput">Auth status not checked yet.</pre>
        <pre id="oauthScopeOutput">Scope not verified yet.</pre>
        <pre id="oauthRevokeOutput">Token not revoked yet.</pre>
      </div>

      <div class="card full">
        <h2>Safe Skill Review &amp; Compilation</h2>
        <p>
          Sprint 3 — Convert a Sprint 2 automation_draft into a safe, versioned skill.
          The flow reviews guards and schema, validates constraints, compiles to the Skill Registry,
          and runs a dry-run proof. No Odoo writes are ever executed.
        </p>
        <div class="toolbar">
          <label>
            Automation Draft ID
            <input id="compileDraftId" placeholder="automation_draft_..." />
          </label>
          <button id="useLatestDraft" type="button">Use latest draft</button>
          <button id="reviewDraft" type="button">Review draft</button>
          <button id="validateDraft" type="button">Validate draft</button>
          <button id="compileDraft" type="button">Compile to skill</button>
          <button id="runDryRunProof" type="button">Run dry-run proof</button>
        </div>
        <p class="tiny" id="compileMessage">Enter a draft id or use the latest draft from Sprint 2.</p>
        <pre id="compileReview">No review yet.</pre>
        <pre id="compileValidation">No validation yet.</pre>
        <pre id="compiledSkill">No compiled skill yet.</pre>
        <pre id="dryRunProof">No dry-run proof yet.</pre>
      </div>
      <div class="card full">
        <h2>Business Analysis & Opportunity Scanner</h2>
        <p>
          Read-only analysis on top of the Sprint 1 Odoo connection. The flow captures a business snapshot,
          derives signals, ranks opportunities, computes ROI, and creates non-executable drafts.
        </p>
        <div class="toolbar">
          <label>
            Odoo Connection ID
            <input id="productConnectionId" placeholder="conn_..." />
          </label>
          <label style="min-width: 220px; gap: 8px; align-items: center; grid-auto-flow: column; justify-content: start;">
            <input id="productIncludeSamples" type="checkbox" checked />
            Include samples
          </label>
          <button id="loadLatestOdooConnection" type="button">Use latest Odoo connection</button>
          <button id="runBusinessAnalysis" type="button">Run business analysis</button>
        </div>
        <p class="tiny" id="productMessage">Read-only mode: no Odoo writes are executed in this sprint.</p>
        <pre id="productSnapshot">No business snapshot yet.</pre>
        <pre id="productSignals">No business signals yet.</pre>
        <div id="recommendationCards" class="analysis-cards"></div>
        <pre id="productROI">No ROI summary yet.</pre>
        <pre id="productDrafts">No automation drafts yet.</pre>
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
    const skillInspector = document.getElementById("skillInspector");
    const runHistory = document.getElementById("runHistory");
    const runTimeline = document.getElementById("runTimeline");
    const approvalGatePlan = document.getElementById("approvalGatePlan");
    const planApprovalGateButton = document.getElementById("planApprovalGate");
    const approvalDecisionSimulation = document.getElementById("approvalDecisionSimulation");
    const simulateApproveGateButton = document.getElementById("simulateApproveGate");
    const simulateRejectGateButton = document.getElementById("simulateRejectGate");
    const teachModeReadiness = document.getElementById("teachModeReadiness");
    const productConnectionIdInput = document.getElementById("productConnectionId");
    const productIncludeSamplesInput = document.getElementById("productIncludeSamples");
    const loadLatestOdooConnectionButton = document.getElementById("loadLatestOdooConnection");
    const runBusinessAnalysisButton = document.getElementById("runBusinessAnalysis");
    const productMessage = document.getElementById("productMessage");
    const productSnapshot = document.getElementById("productSnapshot");
    const productSignals = document.getElementById("productSignals");
    const recommendationCards = document.getElementById("recommendationCards");
    const productROI = document.getElementById("productROI");
    const productDrafts = document.getElementById("productDrafts");
    const marketplaceConnectionIdInput = document.getElementById("marketplaceConnectionId");
    const marketplaceTemplateIdInput = document.getElementById("marketplaceTemplateId");
    const marketplaceConnectorOutput = document.getElementById("marketplaceConnectorOutput");
    const marketplaceTemplateOutput = document.getElementById("marketplaceTemplateOutput");
    const marketplaceRequirementsOutput = document.getElementById("marketplaceRequirementsOutput");
    const marketplaceInstallOutput = document.getElementById("marketplaceInstallOutput");
    const agentBuilderTemplateIdInput = document.getElementById("agentBuilderTemplateId");
    const agentBuilderConnectorIdInput = document.getElementById("agentBuilderConnectorId");
    const agentBuilderConnectionIdInput = document.getElementById("agentBuilderConnectionId");
    const agentBuilderSessionOutput = document.getElementById("agentBuilderSessionOutput");
    const agentBuilderStepLibraryOutput = document.getElementById("agentBuilderStepLibraryOutput");
    const agentBuilderPreviewOutput = document.getElementById("agentBuilderPreviewOutput");
    const agentBuilderDraftOutput = document.getElementById("agentBuilderDraftOutput");
    const connectorAuthConnectorIdInput = document.getElementById("connectorAuthConnectorId");
    const connectorAuthScopeInput = document.getElementById("connectorAuthScope");
    const connectorScopesOutput = document.getElementById("connectorScopesOutput");
    const connectorAuthProfileOutput = document.getElementById("connectorAuthProfileOutput");
    const connectorAuthTestOutput = document.getElementById("connectorAuthTestOutput");
    const connectorAuthAuditOutput = document.getElementById("connectorAuthAuditOutput");

    const humanState = {
      recordingId: null,
      skillId: null,
      versionId: null,
      fakeErpOpened: false,
      recordingFinished: false,
      proofRun: false,
    };

    const productState = {
      analysis: null,
      drafts: [],
    };

    const agentBuilderState = {
      sessionId: null,
    };

    const connectorAuthState = {
      profileId: null,
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

    const escapeHtml = (value) => String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");

    const renderProductDrafts = () => {
      productDrafts.textContent = productState.drafts.length ? jsonText(productState.drafts) : "No automation drafts yet.";
    };

    const renderRecommendationCards = (cards) => {
      if (!cards.length) {
        recommendationCards.innerHTML = "<p class='tiny'>No recommendation cards yet.</p>";
        return;
      }

      recommendationCards.innerHTML = cards.map((card) => `
        <article class="analysis-card">
          <h4>${escapeHtml(card.title)}</h4>
          <div class="meta">
            <span class="analysis-pill">Priority ${escapeHtml(card.priority)}</span>
            <span class="analysis-pill">ROI ${escapeHtml(card.roi?.score ?? 0)}/100</span>
            <span class="analysis-pill">${escapeHtml(card.category)}</span>
          </div>
          <p>${escapeHtml(card.description)}</p>
          <p class="tiny">${escapeHtml(card.recommendation)}</p>
          <p class="tiny">Effort: ${escapeHtml(card.roi?.implementation_effort_hours ?? 0)}h · Monthly value: €${escapeHtml(card.roi?.estimated_monthly_value_eur ?? 0)}</p>
          <button type="button" data-draft-opportunity-id="${escapeHtml(card.opportunity_id)}">Create non-executable draft</button>
        </article>
      `).join("");

      recommendationCards.querySelectorAll("[data-draft-opportunity-id]").forEach((button) => {
        button.addEventListener("click", async () => {
          const opportunityId = button.getAttribute("data-draft-opportunity-id");
          if (!opportunityId) {
            return;
          }

          button.disabled = true;
          productMessage.textContent = `Creating dry-run draft for ${opportunityId}...`;
          try {
            const response = await fetch(`/v1/product/opportunities/${opportunityId}/draft`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
            });
            const body = await response.json();
            if (!response.ok) {
              productMessage.textContent = `Draft unavailable: ${body?.error?.message || "unknown error"}`;
              return;
            }

            productState.drafts = [body, ...productState.drafts.filter((draft) => draft.draft_id !== body.draft_id)];
            productMessage.textContent = `Draft created: ${body.name}`;
            renderProductDrafts();
          } catch (error) {
            productMessage.textContent = `Draft request failed: ${String(error)}`;
          } finally {
            button.disabled = false;
          }
        });
      });
    };

    const marketplaceConfiguration = () => ({
      connection_id: marketplaceConnectionIdInput.value.trim() || "conn_marketplace_demo",
    });

    const loadMarketplaceConnectors = async () => {
      marketplaceConnectorOutput.textContent = "Loading connector catalog...";
      const response = await fetch("/v1/marketplace/connectors");
      const body = await response.json();
      marketplaceConnectorOutput.textContent = response.ok ? jsonText(body) : `Connector catalog failed: ${body?.error?.message || "unknown error"}`;
    };

    const loadMarketplaceTemplates = async () => {
      marketplaceTemplateOutput.textContent = "Loading skill template catalog...";
      const response = await fetch("/v1/marketplace/skill-templates");
      const body = await response.json();
      marketplaceTemplateOutput.textContent = response.ok ? jsonText(body) : `Skill template catalog failed: ${body?.error?.message || "unknown error"}`;
    };

    const checkMarketplaceRequirements = async () => {
      const templateId = marketplaceTemplateIdInput.value.trim() || "odoo_formula_preflight";
      marketplaceRequirementsOutput.textContent = `Checking requirements for ${templateId}...`;
      const response = await fetch(`/v1/marketplace/skill-templates/${templateId}/check-requirements`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ configuration: marketplaceConfiguration() }),
      });
      const body = await response.json();
      marketplaceRequirementsOutput.textContent = response.ok ? jsonText(body) : `Requirements check failed: ${body?.error?.message || "unknown error"}`;
    };

    const installMarketplaceDraft = async () => {
      const templateId = marketplaceTemplateIdInput.value.trim() || "odoo_formula_preflight";
      marketplaceInstallOutput.textContent = `Installing ${templateId} as draft...`;
      const response = await fetch(`/v1/marketplace/skill-templates/${templateId}/install-draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ configuration: marketplaceConfiguration() }),
      });
      const body = await response.json();
      if (!response.ok) {
        marketplaceInstallOutput.textContent = `Install failed: ${body?.error?.message || "unknown error"}`;
        return;
      }
      marketplaceInstallOutput.textContent = jsonText({
        status: body.status,
        template_id: body.template_id,
        draft_id: body.draft?.draft_id,
        review_id: body.review?.review_id,
        next_steps: body.next_steps,
        safety_summary: body.safety_summary,
      });
      if (body.draft?.draft_id) {
        compileDraftIdInput.value = body.draft.draft_id;
      }
    };

    const loadMarketplaceInstalled = async () => {
      const response = await fetch("/v1/marketplace/installed");
      const body = await response.json();
      marketplaceInstallOutput.textContent = response.ok ? jsonText(body) : `Installed drafts failed: ${body?.error?.message || "unknown error"}`;
    };

    const createAgentBuilderSession = async () => {
      const response = await fetch("/v1/agent-builder/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ created_by: defaults.actor }),
      });
      const body = await response.json();
      if (!response.ok) {
        agentBuilderSessionOutput.textContent = `Builder session failed: ${body?.error?.message || "unknown error"}`;
        return;
      }
      agentBuilderState.sessionId = body.session_id;
      agentBuilderSessionOutput.textContent = jsonText(body);
    };

    const loadAgentBuilderStepLibrary = async () => {
      const response = await fetch("/v1/agent-builder/step-library");
      const body = await response.json();
      agentBuilderStepLibraryOutput.textContent = response.ok ? jsonText(body) : `Step library failed: ${body?.error?.message || "unknown error"}`;
    };

    const configureAgentBuilder = async () => {
      if (!agentBuilderState.sessionId) {
        await createAgentBuilderSession();
      }
      const sessionId = agentBuilderState.sessionId;
      const templateId = agentBuilderTemplateIdInput.value.trim() || "odoo_formula_preflight";
      const connectorId = agentBuilderConnectorIdInput.value.trim() || "odoo";
      const connectionId = agentBuilderConnectionIdInput.value.trim() || marketplaceConnectionIdInput.value.trim() || "conn_builder_demo";
      const calls = [
        fetch(`/v1/agent-builder/sessions/${sessionId}/select-template`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ template_id: templateId }) }),
        fetch(`/v1/agent-builder/sessions/${sessionId}/select-connector`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ connector_id: connectorId }) }),
        fetch(`/v1/agent-builder/sessions/${sessionId}/configure-trigger`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ trigger: { type: "manual" } }) }),
        fetch(`/v1/agent-builder/sessions/${sessionId}/configure-inputs`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ inputs: { connection_id: connectionId, order_reference: "S00042" } }) }),
        fetch(`/v1/agent-builder/sessions/${sessionId}/configure-steps`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ steps: ["load_context", "read_record", "run_guard", "produce_decision"] }) }),
        fetch(`/v1/agent-builder/sessions/${sessionId}/configure-guards`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ guards: ["no_generic_writes", "no_r3_r4_writes", "no_raw_tool_execution", "requires_human_review", "formula_guard", "odoo_readonly_guard"] }) }),
        fetch(`/v1/agent-builder/sessions/${sessionId}/check-requirements`, { method: "POST" }),
      ];
      const responses = await Promise.all(calls);
      const bodies = await Promise.all(responses.map((response) => response.json()));
      agentBuilderSessionOutput.textContent = jsonText({ session_id: sessionId, configured: responses.every((response) => response.ok), results: bodies });
    };

    const previewAgentBuilder = async () => {
      if (!agentBuilderState.sessionId) {
        agentBuilderPreviewOutput.textContent = "Create and configure a builder session first.";
        return;
      }
      const response = await fetch(`/v1/agent-builder/sessions/${agentBuilderState.sessionId}/preview`);
      const body = await response.json();
      agentBuilderPreviewOutput.textContent = response.ok ? jsonText(body) : `Preview failed: ${body?.error?.message || "unknown error"}`;
    };

    const saveAgentBuilderDraft = async () => {
      if (!agentBuilderState.sessionId) {
        agentBuilderDraftOutput.textContent = "Create and configure a builder session first.";
        return;
      }
      const response = await fetch(`/v1/agent-builder/sessions/${agentBuilderState.sessionId}/save-draft`, { method: "POST" });
      const body = await response.json();
      if (!response.ok) {
        agentBuilderDraftOutput.textContent = `Save failed: ${body?.error?.message || "unknown error"}`;
        return;
      }
      agentBuilderDraftOutput.textContent = jsonText(body);
      if (body.automation_draft_id) {
        compileDraftIdInput.value = body.automation_draft_id;
      }
    };

    const loadConnectorScopes = async () => {
      const response = await fetch("/v1/connectors/scopes");
      const body = await response.json();
      connectorScopesOutput.textContent = response.ok ? jsonText(body) : `Scopes failed: ${body?.error?.message || "unknown error"}`;
    };

    const connectorAuthPayload = (secretValue) => ({
      connector_id: connectorAuthConnectorIdInput.value.trim() || "gmail",
      display_name: "Demo connector auth profile",
      auth_type: "oauth_placeholder",
      requested_scopes: [connectorAuthScopeInput.value.trim() || "gmail.readonly"],
      credential: { access_token: secretValue },
      created_by: defaults.actor,
    });

    const createConnectorAuthProfile = async () => {
      const response = await fetch("/v1/connectors/auth-profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(connectorAuthPayload("demo_secret_redacted")),
      });
      const body = await response.json();
      if (!response.ok) {
        connectorAuthProfileOutput.textContent = `Auth profile failed: ${body?.error?.message || "unknown error"}`;
        return;
      }
      connectorAuthState.profileId = body.profile_id;
      connectorAuthProfileOutput.textContent = jsonText(body);
    };

    const testConnectorAuthProfile = async () => {
      if (!connectorAuthState.profileId) {
        connectorAuthTestOutput.textContent = "Create a connector auth profile first.";
        return;
      }
      const response = await fetch(`/v1/connectors/auth-profiles/${connectorAuthState.profileId}/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor: defaults.actor }),
      });
      const body = await response.json();
      connectorAuthTestOutput.textContent = response.ok ? jsonText(body) : `Test failed: ${body?.error?.message || "unknown error"}`;
    };

    const rotateConnectorAuthProfile = async () => {
      if (!connectorAuthState.profileId) {
        connectorAuthProfileOutput.textContent = "Create a connector auth profile first.";
        return;
      }
      const response = await fetch(`/v1/connectors/auth-profiles/${connectorAuthState.profileId}/rotate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential: { access_token: "rotated_secret_redacted" }, actor: defaults.actor }),
      });
      const body = await response.json();
      connectorAuthProfileOutput.textContent = response.ok ? jsonText(body) : `Rotate failed: ${body?.error?.message || "unknown error"}`;
    };

    const revokeConnectorAuthProfile = async () => {
      if (!connectorAuthState.profileId) {
        connectorAuthProfileOutput.textContent = "Create a connector auth profile first.";
        return;
      }
      const response = await fetch(`/v1/connectors/auth-profiles/${connectorAuthState.profileId}/revoke`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor: defaults.actor }),
      });
      const body = await response.json();
      connectorAuthProfileOutput.textContent = response.ok ? jsonText(body) : `Revoke failed: ${body?.error?.message || "unknown error"}`;
    };

    const loadConnectorAuthAudit = async () => {
      if (!connectorAuthState.profileId) {
        connectorAuthAuditOutput.textContent = "Create a connector auth profile first.";
        return;
      }
      const response = await fetch(`/v1/connectors/auth-profiles/${connectorAuthState.profileId}/audit`);
      const body = await response.json();
      connectorAuthAuditOutput.textContent = response.ok ? jsonText(body) : `Audit failed: ${body?.error?.message || "unknown error"}`;
    };

    const renderProductAnalysis = (result) => {
      productState.analysis = result;
      productState.drafts = [];
      productMessage.textContent = `Analysis completed for ${result.connection_id}.`;
      productSnapshot.textContent = jsonText({
        snapshot_id: result.snapshot_id,
        status: result.snapshot.status,
        read_only_mode: result.snapshot.read_only_mode,
        odoo: result.snapshot.odoo,
        detected: result.snapshot.detected,
        warnings: result.snapshot.warnings,
        next_recommended_action: result.snapshot.next_recommended_action,
      });
      productSignals.textContent = jsonText(result.signals || []);
      productROI.textContent = jsonText(result.roi_summary || {});
      renderRecommendationCards(result.recommendation_cards || []);
      renderProductDrafts();
    };

    const loadLatestOdooConnection = async () => {
      productMessage.textContent = "Loading latest Odoo connection...";
      try {
        const response = await fetch("/v1/connections");
        const body = await response.json();
        if (!response.ok) {
          productMessage.textContent = `Could not load connections: ${body?.error?.message || "unknown error"}`;
          return;
        }

        const latestOdoo = (body || []).find((connection) => connection.erp_type === "odoo");
        if (!latestOdoo) {
          productMessage.textContent = "No Odoo connection found yet.";
          return;
        }

        productConnectionIdInput.value = latestOdoo.id;
        productMessage.textContent = `Loaded latest Odoo connection ${latestOdoo.id}.`;
      } catch (error) {
        productMessage.textContent = `Could not load latest Odoo connection: ${String(error)}`;
      }
    };

    const runBusinessAnalysis = async () => {
      const connectionId = productConnectionIdInput.value.trim();
      if (!connectionId) {
        productMessage.textContent = "Enter or load an Odoo connection id first.";
        return;
      }

      runBusinessAnalysisButton.disabled = true;
      productMessage.textContent = `Running business analysis for ${connectionId}...`;
      try {
        const response = await fetch(`/v1/product/connections/${connectionId}/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            include_samples: productIncludeSamplesInput.checked,
            sample_limits: { sales_orders: 5, products: 5, custom_fields: 50 },
            max_opportunities: 5,
          }),
        });
        const body = await response.json();
        if (!response.ok) {
          productMessage.textContent = `Business analysis unavailable: ${body?.error?.message || "unknown error"}`;
          return;
        }

        renderProductAnalysis(body);
      } catch (error) {
        productMessage.textContent = `Business analysis request failed: ${String(error)}`;
      } finally {
        runBusinessAnalysisButton.disabled = false;
      }
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

    const renderSkillInspector = (inspection) => {
      skillInspector.textContent = jsonText({
        skill_id: inspection.skill_id,
        name: inspection.name,
        version_id: inspection.version_id,
        runtime_type: inspection.runtime_type,
        llm_required_for_repeated_runs: inspection.llm_required_for_repeated_runs,
        inputs: inspection.inputs,
        guards: inspection.guards,
        workflow_steps: inspection.workflow_steps,
        compiled_from_recording_id: inspection.compiled_from_recording_id,
        safety_summary: inspection.safety_summary,
      });
    };

    const renderRunHistory = (history, timelinePreview) => {
      runHistory.textContent = jsonText(history);
      runTimeline.textContent = timelinePreview ? jsonText(timelinePreview) : "No audit timeline yet.";
    };

    const refreshRunHistory = async () => {
      if (!humanState.skillId) {
        runHistory.textContent = "No run history yet.";
        runTimeline.textContent = "No audit timeline yet.";
        return null;
      }

      const response = await fetch(`/v1/skills/${humanState.skillId}/runs`);
      const body = await response.json();
      if (!response.ok) {
        runHistory.textContent = `Run history unavailable: ${body?.error?.message || "unknown error"}`;
        runTimeline.textContent = "No audit timeline yet.";
        return null;
      }

      const latestRun = body.runs?.[0];
      if (!latestRun) {
        renderRunHistory(body, null);
        return body;
      }

      const timelineResponse = await fetch(`/v1/skills/${humanState.skillId}/runs/${latestRun.skill_run_id}/timeline`);
      const timelineBody = await timelineResponse.json();
      if (!timelineResponse.ok) {
        renderRunHistory(body, { error: timelineBody?.error?.message || "unknown error" });
        return body;
      }

      renderRunHistory(body, timelineBody);
      return body;
    };

    const refreshSkillInspector = async () => {
      if (!humanState.skillId) {
        skillInspector.textContent = "No inspected skill yet.";
        return null;
      }

      const response = await fetch(`/v1/skills/${humanState.skillId}/inspect`);
      const body = await response.json();
      if (!response.ok) {
        skillInspector.textContent = `Inspector unavailable: ${body?.error?.message || "unknown error"}`;
        return null;
      }

      renderSkillInspector(body);
      return body;
    };

    const refreshApprovalGatePlan = async () => {
      if (!humanState.skillId) {
        approvalGatePlan.textContent = "No approval plan yet.";
        return null;
      }

      const response = await fetch(`/v1/skills/${humanState.skillId}/plan-action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          inputs: { order_reference: "SO-VALID" },
          requested_action: "confirm_sales_order",
        }),
      });
      const body = await response.json();
      if (!response.ok) {
        approvalGatePlan.textContent = `Approval plan unavailable: ${body?.error?.message || "unknown error"}`;
        return null;
      }

      approvalGatePlan.textContent = jsonText(body);
      return body;
    };

    const refreshApprovalDecisionSimulation = async (orderReference, decision) => {
      if (!humanState.skillId) {
        approvalDecisionSimulation.textContent = "No approval decision simulated yet.";
        return null;
      }

      const response = await fetch(`/v1/skills/${humanState.skillId}/simulate-approval-decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          inputs: { order_reference: orderReference },
          requested_action: "confirm_sales_order",
          decision,
          approver: { type: "user", id: "demo_approver", display_name: "Demo Approver" },
          reason: decision === "approve" ? "Formula preview is clean." : "Formula Guard blocks this order.",
        }),
      });
      const body = await response.json();
      if (!response.ok) {
        approvalDecisionSimulation.textContent = `Approval decision unavailable: ${body?.error?.message || "unknown error"}`;
        return null;
      }

      approvalDecisionSimulation.textContent = jsonText(body);
      return body;
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
        await refreshSkillInspector();
        approvalGatePlan.textContent = "No approval plan yet.";
        approvalDecisionSimulation.textContent = "No approval decision simulated yet.";
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
        await refreshSkillInspector();
        await refreshRunHistory();
      } catch (error) {
        setHumanResults(`Failed to run compiled skill: ${String(error)}`);
      } finally {
        runHumanRecordingButton.disabled = false;
      }
    });

    planApprovalGateButton.addEventListener("click", async () => {
      if (!humanState.skillId) {
        approvalGatePlan.textContent = "Compile the human recording first.";
        return;
      }

      planApprovalGateButton.disabled = true;
      approvalGatePlan.textContent = "Generating safe action plan...";
      try {
        await refreshApprovalGatePlan();
      } catch (error) {
        approvalGatePlan.textContent = `Failed to generate approval plan: ${String(error)}`;
      } finally {
        planApprovalGateButton.disabled = false;
      }
    });

    simulateApproveGateButton.addEventListener("click", async () => {
      if (!humanState.skillId) {
        approvalDecisionSimulation.textContent = "Compile the human recording first.";
        return;
      }

      simulateApproveGateButton.disabled = true;
      approvalDecisionSimulation.textContent = "Simulating approval decision...";
      try {
        await refreshApprovalDecisionSimulation("SO-VALID", "approve");
      } catch (error) {
        approvalDecisionSimulation.textContent = `Failed to simulate approval decision: ${String(error)}`;
      } finally {
        simulateApproveGateButton.disabled = false;
      }
    });

    simulateRejectGateButton.addEventListener("click", async () => {
      if (!humanState.skillId) {
        approvalDecisionSimulation.textContent = "Compile the human recording first.";
        return;
      }

      simulateRejectGateButton.disabled = true;
      approvalDecisionSimulation.textContent = "Simulating rejection decision...";
      try {
        await refreshApprovalDecisionSimulation("SO-FORMULA-MISMATCH", "reject");
      } catch (error) {
        approvalDecisionSimulation.textContent = `Failed to simulate approval decision: ${String(error)}`;
      } finally {
        simulateRejectGateButton.disabled = false;
      }
    });

    const approvalSkillIdInput = document.getElementById("approvalSkillId");
    const approvalRequesterNameInput = document.getElementById("approvalRequesterName");
    const approvalApproverNameInput = document.getElementById("approvalApproverName");
    const approvalMessage = document.getElementById("approvalMessage");
    const approvalRequestOutput = document.getElementById("approvalRequestOutput");
    const approvalDecisionOutput = document.getElementById("approvalDecisionOutput");
    const activationGateOutput = document.getElementById("activationGateOutput");
    const governanceSummaryOutput = document.getElementById("governanceSummaryOutput");

    const approvalState = { skillId: null };

    const getApprovalSkillId = () => approvalSkillIdInput.value.trim() || approvalState.skillId;

    document.getElementById("submitApprovalRequest").addEventListener("click", async () => {
      const skillId = getApprovalSkillId();
      if (!skillId) { approvalMessage.textContent = "Enter a skill id first (or compile a draft in Sprint 3)."; return; }
      approvalState.skillId = skillId;
      approvalMessage.textContent = `Submitting approval request for ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/approval-request`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            requested_by: { type: "user", id: "demo_operator", display_name: approvalRequesterNameInput.value.trim() || "Demo Operator" },
            reason: "Requesting governance approval for dry-run skill activation.",
            context: {},
          }),
        });
        const body = await response.json();
        if (!response.ok) {
          approvalRequestOutput.textContent = `Request failed: ${body?.error?.message || "unknown error"}`;
          return;
        }
        approvalRequestOutput.textContent = jsonText({
          request_id: body.request_id,
          status: body.status,
          can_execute_real_writes: body.can_execute_real_writes,
          requested_by: body.requested_by,
          reason: body.reason,
        });
        approvalMessage.textContent = `Approval request submitted: ${body.request_id}`;
      } catch (error) {
        approvalRequestOutput.textContent = `Request failed: ${String(error)}`;
      }
    });

    document.getElementById("approveSkill").addEventListener("click", async () => {
      const skillId = getApprovalSkillId();
      if (!skillId) { approvalMessage.textContent = "Submit an approval request first."; return; }
      approvalMessage.textContent = `Approving skill ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/approval-decision`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            decided_by: { type: "user", id: "demo_approver", display_name: approvalApproverNameInput.value.trim() || "Demo Approver" },
            decision: "approve",
            reason: "Dry-run proof passed. Guards verified. Approved for governance state only.",
          }),
        });
        const body = await response.json();
        if (!response.ok) {
          approvalDecisionOutput.textContent = `Decision failed: ${body?.error?.message || "unknown error"}`;
          return;
        }
        approvalDecisionOutput.textContent = jsonText({
          decision_id: body.decision_id,
          decision: body.decision,
          can_execute_real_writes: body.can_execute_real_writes,
          approved_for_real_execution: body.approved_for_real_execution,
          decided_by: body.decided_by,
        });
        approvalMessage.textContent = `Decision recorded: ${body.decision}`;
      } catch (error) {
        approvalDecisionOutput.textContent = `Decision failed: ${String(error)}`;
      }
    });

    document.getElementById("rejectSkill").addEventListener("click", async () => {
      const skillId = getApprovalSkillId();
      if (!skillId) { approvalMessage.textContent = "Submit an approval request first."; return; }
      approvalMessage.textContent = `Rejecting skill ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/approval-decision`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            decided_by: { type: "user", id: "demo_approver", display_name: approvalApproverNameInput.value.trim() || "Demo Approver" },
            decision: "reject",
            reason: "Skill does not meet current governance criteria.",
          }),
        });
        const body = await response.json();
        if (!response.ok) {
          approvalDecisionOutput.textContent = `Decision failed: ${body?.error?.message || "unknown error"}`;
          return;
        }
        approvalDecisionOutput.textContent = jsonText(body);
        approvalMessage.textContent = `Decision recorded: ${body.decision}`;
      } catch (error) {
        approvalDecisionOutput.textContent = `Decision failed: ${String(error)}`;
      }
    });

    document.getElementById("runActivationGate").addEventListener("click", async () => {
      const skillId = getApprovalSkillId();
      if (!skillId) { approvalMessage.textContent = "Enter a skill id first."; return; }
      approvalMessage.textContent = `Running activation gate for ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/activation-gate`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) {
          activationGateOutput.textContent = `Gate failed: ${body?.error?.message || "unknown error"}`;
          return;
        }
        activationGateOutput.textContent = jsonText({
          gate_id: body.gate_id,
          gate_status: body.gate_status,
          can_activate: body.can_activate,
          can_execute_real_writes: body.can_execute_real_writes,
          approved_for_real_execution: body.approved_for_real_execution,
          checks: (body.checks || []).map((c) => ({ id: c.check_id, passed: c.passed, detail: c.detail })),
        });
        approvalMessage.textContent = `Activation gate: ${body.gate_status}`;
      } catch (error) {
        activationGateOutput.textContent = `Gate failed: ${String(error)}`;
      }
    });

    document.getElementById("getGovernanceSummary").addEventListener("click", async () => {
      const skillId = getApprovalSkillId();
      if (!skillId) { approvalMessage.textContent = "Enter a skill id first."; return; }
      approvalMessage.textContent = `Loading governance summary for ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/governance-summary`);
        const body = await response.json();
        if (!response.ok) {
          governanceSummaryOutput.textContent = `Summary failed: ${body?.error?.message || "unknown error"}`;
          return;
        }
        governanceSummaryOutput.textContent = jsonText({
          skill_id: body.skill_id,
          governance_state: body.governance_state,
          can_execute_real_writes: body.can_execute_real_writes,
          approved_for_real_execution: body.approved_for_real_execution,
          next_required_action: body.next_required_action,
          latest_decision: body.latest_decision?.decision || null,
          gate_status: body.latest_gate?.gate_status || null,
        });
        approvalMessage.textContent = `Governance state: ${body.governance_state}`;
      } catch (error) {
        governanceSummaryOutput.textContent = `Summary failed: ${String(error)}`;
      }
    });

    const compileDraftIdInput = document.getElementById("compileDraftId");
    const compileMessage = document.getElementById("compileMessage");
    const compileReview = document.getElementById("compileReview");
    const compileValidation = document.getElementById("compileValidation");
    const compiledSkill = document.getElementById("compiledSkill");
    const dryRunProof = document.getElementById("dryRunProof");
    const useLatestDraftButton = document.getElementById("useLatestDraft");
    const reviewDraftButton = document.getElementById("reviewDraft");
    const validateDraftButton = document.getElementById("validateDraft");
    const compileDraftButton = document.getElementById("compileDraft");
    const runDryRunProofButton = document.getElementById("runDryRunProof");

    const compileState = { skillId: null };

    useLatestDraftButton.addEventListener("click", async () => {
      compileMessage.textContent = "Loading latest automation draft...";
      try {
        const response = await fetch("/v1/connections");
        const connections = await response.json();
        if (!response.ok || !connections.length) {
          compileMessage.textContent = "No connections found. Run Sprint 2 analysis first.";
          return;
        }
        const latestOdoo = (connections || []).find((c) => c.erp_type === "odoo");
        if (!latestOdoo) {
          compileMessage.textContent = "No Odoo connection found.";
          return;
        }
        const analysisResponse = await fetch(`/v1/product/connections/${latestOdoo.id}/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ include_samples: true, sample_limits: { sales_orders: 3, products: 3, custom_fields: 30 }, max_opportunities: 1 }),
        });
        const analysisBody = await analysisResponse.json();
        if (!analysisResponse.ok || !analysisBody.opportunities?.length) {
          compileMessage.textContent = "Could not get opportunities to draft.";
          return;
        }
        const firstOpportunityId = analysisBody.opportunities[0].opportunity_id;
        const draftResponse = await fetch(`/v1/product/opportunities/${firstOpportunityId}/draft`, { method: "POST" });
        const draftBody = await draftResponse.json();
        if (!draftResponse.ok) {
          compileMessage.textContent = `Draft creation failed: ${draftBody?.error?.message || "unknown error"}`;
          return;
        }
        compileDraftIdInput.value = draftBody.draft_id;
        compileMessage.textContent = `Loaded draft ${draftBody.draft_id} for opportunity '${analysisBody.opportunities[0].title}'.`;
      } catch (error) {
        compileMessage.textContent = `Failed to load latest draft: ${String(error)}`;
      }
    });

    reviewDraftButton.addEventListener("click", async () => {
      const draftId = compileDraftIdInput.value.trim();
      if (!draftId) { compileMessage.textContent = "Enter or load a draft id first."; return; }
      reviewDraftButton.disabled = true;
      compileMessage.textContent = `Reviewing draft ${draftId}...`;
      try {
        const response = await fetch(`/v1/product/automation-drafts/${draftId}/review`);
        const body = await response.json();
        if (!response.ok) {
          compileReview.textContent = `Review unavailable: ${body?.error?.message || "unknown error"}`;
          return;
        }
        compileReview.textContent = jsonText({
          review_id: body.review_id,
          status: body.status,
          guards: (body.guards || []).map((g) => g.name),
          input_schema: (body.input_schema || []).map((f) => `${f.name}: ${f.type}`),
          output_schema: (body.output_schema || []).map((f) => `${f.name}: ${f.type}`),
          test_cases: (body.test_cases || []).map((tc) => tc.case_id),
        });
        compileMessage.textContent = `Review ready: ${body.review_id}`;
      } catch (error) {
        compileReview.textContent = `Review request failed: ${String(error)}`;
      } finally {
        reviewDraftButton.disabled = false;
      }
    });

    validateDraftButton.addEventListener("click", async () => {
      const draftId = compileDraftIdInput.value.trim();
      if (!draftId) { compileMessage.textContent = "Enter or load a draft id first."; return; }
      validateDraftButton.disabled = true;
      compileMessage.textContent = `Validating draft ${draftId}...`;
      try {
        const response = await fetch(`/v1/product/automation-drafts/${draftId}/validate`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) {
          compileValidation.textContent = `Validation unavailable: ${body?.error?.message || "unknown error"}`;
          return;
        }
        compileValidation.textContent = jsonText(body);
        compileMessage.textContent = body.passed ? `Validation passed for ${draftId}.` : `Validation failed: ${body.issues?.length} issue(s).`;
      } catch (error) {
        compileValidation.textContent = `Validation request failed: ${String(error)}`;
      } finally {
        validateDraftButton.disabled = false;
      }
    });

    compileDraftButton.addEventListener("click", async () => {
      const draftId = compileDraftIdInput.value.trim();
      if (!draftId) { compileMessage.textContent = "Enter or load a draft id first."; return; }
      compileDraftButton.disabled = true;
      compileMessage.textContent = `Compiling draft ${draftId} to skill...`;
      try {
        const response = await fetch(`/v1/product/automation-drafts/${draftId}/compile-skill`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) {
          compiledSkill.textContent = `Compilation failed: ${body?.error?.message || "unknown error"}`;
          return;
        }
        compileState.skillId = body.skill_id;
        compiledSkill.textContent = jsonText({
          skill_id: body.skill_id,
          version_id: body.version_id,
          name: body.name,
          runtime_mode: body.runtime_mode,
          write_actions: body.write_actions,
          requires_approval_before_activation: body.requires_approval_before_activation,
          guards: body.guards,
        });
        compileMessage.textContent = `Skill compiled: ${body.skill_id}`;
      } catch (error) {
        compiledSkill.textContent = `Compilation request failed: ${String(error)}`;
      } finally {
        compileDraftButton.disabled = false;
      }
    });

    runDryRunProofButton.addEventListener("click", async () => {
      if (!compileState.skillId) { compileMessage.textContent = "Compile the draft to a skill first."; return; }
      runDryRunProofButton.disabled = true;
      compileMessage.textContent = `Running dry-run proof for ${compileState.skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${compileState.skillId}/dry-run-proof`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) {
          dryRunProof.textContent = `Dry-run proof failed: ${body?.error?.message || "unknown error"}`;
          return;
        }
        dryRunProof.textContent = jsonText({
          proof_id: body.proof_id,
          status: body.status,
          cases_total: body.cases_total,
          cases_passed: body.cases_passed,
          write_actions: body.write_actions,
          runtime_mode: body.runtime_mode,
          requires_approval_before_activation: body.requires_approval_before_activation,
          case_results: (body.case_results || []).map((r) => ({
            case_id: r.case_id,
            passed: r.passed,
            actual_decision: r.actual_decision,
          })),
        });
        compileMessage.textContent = `Dry-run proof ${body.status}: ${body.cases_passed}/${body.cases_total} cases passed.`;
      } catch (error) {
        dryRunProof.textContent = `Dry-run proof request failed: ${String(error)}`;
      } finally {
        runDryRunProofButton.disabled = false;
      }
    });

    // Sprint 12 — Release Candidate v0.12.0-rc1 — Operator Demo Pack
    const rcMessage = document.getElementById("rcMessage");
    const rcHealthOutput = document.getElementById("rc-health-output");
    const rcReadinessOutput = document.getElementById("rc-readiness-output");
    const rcSeedOutput = document.getElementById("rc-seed-output");
    const rcSmokeOutput = document.getElementById("rc-smoke-output");
    const rcSafetyOutput = document.getElementById("rc-safety-output");

    document.getElementById("rcHealth").addEventListener("click", async () => {
      rcMessage.textContent = "Checking release health...";
      try {
        const response = await fetch("/v1/release/health");
        const body = await response.json();
        rcHealthOutput.textContent = jsonText({
          status: body.status,
          version: body.version,
          db_accessible: body.db_accessible,
          safety_boundaries_locked: body.safety_boundaries_locked,
          safety_boundaries: body.safety_boundaries,
        });
        rcMessage.textContent = `Release health: ${body.status} — v${body.version} — DB: ${body.db_accessible} — Safety locked: ${body.safety_boundaries_locked}`;
      } catch (error) { rcHealthOutput.textContent = `Health check failed: ${String(error)}`; }
    });

    document.getElementById("rcReadiness").addEventListener("click", async () => {
      rcMessage.textContent = "Loading readiness report...";
      try {
        const response = await fetch("/v1/release/readiness-report");
        const body = await response.json();
        rcReadinessOutput.textContent = jsonText({
          release_version: body.release_version,
          status: body.status,
          readiness_score: body.readiness_score,
          checks_passed: body.checks_passed,
          checks_total: body.checks_total,
          checks: (body.checks || []).map(c => ({ name: c.name, passed: c.passed })),
          sprint_chain: (body.sprint_chain || []).length + " sprints",
          entity_counts: body.entity_counts || {},
        });
        rcMessage.textContent = `Readiness: ${body.status} — ${body.readiness_score}% — ${body.checks_passed}/${body.checks_total} checks passed`;
      } catch (error) { rcReadinessOutput.textContent = `Readiness failed: ${String(error)}`; }
    });

    document.getElementById("rcDemoSeed").addEventListener("click", async () => {
      rcMessage.textContent = "Seeding demo data...";
      try {
        const response = await fetch("/v1/release/demo-seed", { method: "POST" });
        const body = await response.json();
        if (!response.ok) { rcSeedOutput.textContent = `Seed failed: ${body?.error?.message || "unknown"}`; return; }
        rcSeedOutput.textContent = jsonText({
          seeded: body.seeded,
          tenant_id: body.tenant_id,
          tenant_name: body.tenant_name,
          skill_id: body.skill_id,
          operator_session_id: body.operator_session_id,
          operator_session_step: body.operator_session_step,
          next_steps: body.next_steps || [],
        });
        rcMessage.textContent = `Demo seeded: tenant=${body.tenant_id} skill=${body.skill_id} session=${body.operator_session_id}`;
      } catch (error) { rcSeedOutput.textContent = `Seed failed: ${String(error)}`; }
    });

    document.getElementById("rcSmoke").addEventListener("click", async () => {
      rcMessage.textContent = "Running operator smoke test...";
      try {
        const response = await fetch("/v1/release/operator-smoke", { method: "POST" });
        const body = await response.json();
        if (!response.ok) { rcSmokeOutput.textContent = `Smoke failed: ${body?.error?.message || "unknown"}`; return; }
        rcSmokeOutput.textContent = jsonText({
          smoke_status: body.smoke_status,
          checks_passed: body.checks_passed,
          checks_total: body.checks_total,
          checks: (body.checks || []).map(c => ({ name: c.name, passed: c.passed, detail: c.detail })),
          safety_invariants: body.safety_invariants,
        });
        rcMessage.textContent = `Smoke test: ${body.smoke_status} — ${body.checks_passed}/${body.checks_total} checks`;
      } catch (error) { rcSmokeOutput.textContent = `Smoke failed: ${String(error)}`; }
    });

    document.getElementById("rcSafetyBoundaries").addEventListener("click", async () => {
      rcMessage.textContent = "Loading safety boundaries...";
      try {
        const response = await fetch("/v1/release/safety-boundaries");
        const body = await response.json();
        rcSafetyOutput.textContent = jsonText({
          safety_boundaries: body.safety_boundaries,
          allowed_r1_models: body.allowed_r1_models,
          allowed_r2_models: body.allowed_r2_models,
          allowed_r2_fields: body.allowed_r2_fields,
          allowed_environments: body.allowed_environments,
          blocked_operations: body.blocked_operations,
          notes: body.notes,
        });
        rcMessage.textContent = `Safety boundaries loaded. R1: ${(body.allowed_r1_models || []).join(", ")}. R2: ${(body.allowed_r2_models || []).join(", ")}.`;
      } catch (error) { rcSafetyOutput.textContent = `Safety boundaries failed: ${String(error)}`; }
    });

    // Sprint 11 — R2 Evidence Review, Rollback Rehearsal & Production Readiness
    const r2rMessage = document.getElementById("r2rMessage");
    const r2rReviewOutput = document.getElementById("r2r-review-output");
    const r2rRehearsalOutput = document.getElementById("r2r-rehearsal-output");
    const r2rReportOutput = document.getElementById("r2r-report-output");
    const r2rGateOutput = document.getElementById("r2r-gate-output");
    const r2rRunIdInput = document.getElementById("r2rRunId");

    const getR2rRunId = () => r2rRunIdInput?.value?.trim() || "";

    document.getElementById("r2rEvidenceReview").addEventListener("click", async () => {
      const runId = getR2rRunId();
      if (!runId) { r2rMessage.textContent = "Enter an R2 run ID first."; return; }
      r2rMessage.textContent = `Loading evidence review for ${runId}...`;
      try {
        const response = await fetch(`/v1/product/r2-write-pilot/runs/${runId}/evidence-review`);
        const body = await response.json();
        if (!response.ok) { r2rReviewOutput.textContent = `Review failed: ${body?.error?.message || "unknown"}`; return; }
        r2rReviewOutput.textContent = jsonText({
          review_id: body.review_id,
          fields_changed: body.fields_changed,
          fields_unchanged: body.fields_unchanged,
          drift_detected: body.drift_detected,
          drift_details: body.drift_details || [],
          delta: body.delta || {},
          rollback_instructions: body.rollback_instructions || {},
          safety_invariants: body.safety_invariants,
        });
        r2rMessage.textContent = `Evidence review: ${body.fields_changed} field(s) changed. Drift: ${body.drift_detected}`;
      } catch (error) { r2rReviewOutput.textContent = `Review failed: ${String(error)}`; }
    });

    document.getElementById("r2rRollbackRehearsal").addEventListener("click", async () => {
      const runId = getR2rRunId();
      if (!runId) { r2rMessage.textContent = "Enter an R2 run ID first."; return; }
      r2rMessage.textContent = `Rehearsing rollback for ${runId} (dry-run only)...`;
      try {
        const response = await fetch(`/v1/product/r2-write-pilot/runs/${runId}/rollback-rehearsal`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) { r2rRehearsalOutput.textContent = `Rehearsal failed: ${body?.error?.message || "unknown"}`; return; }
        r2rRehearsalOutput.textContent = jsonText({
          rehearsal_id: body.rehearsal_id,
          instructions_valid: body.instructions_valid,
          rehearsal_passed: body.rehearsal_passed,
          missing_fields: body.missing_fields,
          dry_run_steps: (body.dry_run_steps || []).map(s => ({ step: s.step, action: s.action, description: s.description })),
          notes: body.notes,
          real_rollback_executed: body.real_rollback_executed,
        });
        r2rMessage.textContent = `Rollback rehearsal: ${body.rehearsal_passed ? "PASSED" : "FAILED"} — ${body.notes}`;
      } catch (error) { r2rRehearsalOutput.textContent = `Rehearsal failed: ${String(error)}`; }
    });

    document.getElementById("r2rExecutionReport").addEventListener("click", async () => {
      const runId = getR2rRunId();
      if (!runId) { r2rMessage.textContent = "Enter an R2 run ID first."; return; }
      r2rMessage.textContent = `Generating execution report for ${runId}...`;
      try {
        const response = await fetch(`/v1/product/r2-write-pilot/runs/${runId}/execution-report`);
        const body = await response.json();
        if (!response.ok) { r2rReportOutput.textContent = `Report failed: ${body?.error?.message || "unknown"}`; return; }
        r2rReportOutput.textContent = jsonText({
          report_id: body.report_id,
          residual_risk_score: body.residual_risk_score,
          risk_level: body.risk_level,
          status: body.status,
          report: body.report || {},
        });
        r2rMessage.textContent = `Execution report: residual risk ${body.residual_risk_score}/100 (${body.risk_level})`;
      } catch (error) { r2rReportOutput.textContent = `Report failed: ${String(error)}`; }
    });

    document.getElementById("r2rPromotionGate").addEventListener("click", async () => {
      const runId = getR2rRunId();
      if (!runId) { r2rMessage.textContent = "Enter an R2 run ID first."; return; }
      r2rMessage.textContent = `Evaluating promotion gate for ${runId}...`;
      try {
        const response = await fetch(`/v1/product/r2-write-pilot/runs/${runId}/promotion-gate`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) { r2rGateOutput.textContent = `Gate failed: ${body?.error?.message || "unknown"}`; return; }
        r2rGateOutput.textContent = jsonText({
          gate_id: body.gate_id,
          gate_status: body.gate_status,
          blocked: body.blocked,
          checks: (body.checks || []).map(c => ({ name: c.name, passed: c.passed })),
          blocking_reasons: body.blocking_reasons || [],
          safety_invariants: body.safety_invariants,
        });
        const passed = (body.checks || []).filter(c => c.passed).length;
        const total = (body.checks || []).length;
        r2rMessage.textContent = `Promotion gate: ${body.gate_status.toUpperCase()} — ${passed}/${total} checks passed`;
      } catch (error) { r2rGateOutput.textContent = `Gate failed: ${String(error)}`; }
    });

    // Sprint 10B — R2 Controlled Write Pilot (res.partner.write, staging only)
    const r2SkillIdInput = document.getElementById("r2SkillId");
    const r2Message = document.getElementById("r2Message");
    const r2RequestOutput = document.getElementById("r2-request-output");
    const r2PolicyOutput = document.getElementById("r2-policy-output");
    const r2RunOutput = document.getElementById("r2-run-output");
    const r2EvidenceOutput = document.getElementById("r2-evidence-output");
    const r2HistoryOutput = document.getElementById("r2-history-output");
    const r2State = { requestId: null, runId: null };

    const getR2SkillId = () => r2SkillIdInput?.value?.trim() || "";

    document.getElementById("r2CreateRequest").addEventListener("click", async () => {
      const skillId = getR2SkillId();
      if (!skillId) { r2Message.textContent = "Enter a skill id first."; return; }
      r2Message.textContent = `Creating R2 write pilot request for ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/r2-write-pilot/request`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            requested_by: { type: "user", id: "demo_operator", display_name: "Demo Operator" },
            approver_1: { type: "user", id: "approver_1", display_name: "Demo Approver 1" },
            approver_2: { type: "user", id: "approver_2", display_name: "Demo Approver 2" },
            target_record_id: 1,
            vals: { comment: "ERPGuard Sprint 10B R2 pilot — staging test annotation." },
            environment: "staging",
          }),
        });
        const body = await response.json();
        if (!response.ok) { r2RequestOutput.textContent = `Request failed: ${body?.error?.message || "unknown"}`; return; }
        r2State.requestId = body.request_id;
        r2RequestOutput.textContent = jsonText({
          request_id: body.request_id,
          target_model: body.target_model,
          target_record_id: body.target_record_id,
          target_fields: body.target_fields,
          environment: body.environment,
          status: body.status,
          allow_r2_real_write_pilot: body.allow_r2_real_write_pilot,
          allow_generic_real_odoo_writes: body.allow_generic_real_odoo_writes,
          idempotency_key: body.idempotency_key,
          duplicate: body._idempotent_duplicate || false,
        });
        r2Message.textContent = `R2 request: ${body.request_id} (target: ${body.target_model} #${body.target_record_id})`;
      } catch (error) { r2RequestOutput.textContent = `Request failed: ${String(error)}`; }
    });

    document.getElementById("r2CheckPolicy").addEventListener("click", async () => {
      if (!r2State.requestId) { r2Message.textContent = "Create an R2 request first."; return; }
      r2Message.textContent = `Checking R2 policy for ${r2State.requestId}...`;
      try {
        const response = await fetch(`/v1/product/r2-write-pilot/requests/${r2State.requestId}/policy-check`, { method: "POST" });
        const body = await response.json();
        r2PolicyOutput.textContent = jsonText({
          passed: body.passed,
          allow_r2_real_write_pilot: body.allow_r2_real_write_pilot,
          allow_generic_real_odoo_writes: body.allow_generic_real_odoo_writes,
          allow_r3_r4_real_writes: body.allow_r3_r4_real_writes,
          target_model: body.target_model,
          target_model_whitelisted: body.target_model_whitelisted,
          target_fields: body.target_fields,
          target_fields_whitelisted: body.target_fields_whitelisted,
          violations: body.violations || [],
        });
        r2Message.textContent = `R2 policy: ${body.passed ? "PASSED" : "BLOCKED (" + (body.violations || []).length + " violation(s))"}`;
      } catch (error) { r2PolicyOutput.textContent = `Policy check failed: ${String(error)}`; }
    });

    document.getElementById("r2Execute").addEventListener("click", async () => {
      if (!r2State.requestId) { r2Message.textContent = "Create an R2 request first."; return; }
      r2Message.textContent = `Executing R2 pilot for ${r2State.requestId}...`;
      try {
        const response = await fetch(`/v1/product/r2-write-pilot/requests/${r2State.requestId}/execute`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) { r2RunOutput.textContent = `Execute failed: ${body?.error?.message || "unknown"}`; return; }
        r2State.runId = body.run_id;
        r2RunOutput.textContent = jsonText({
          run_id: body.run_id,
          status: body.status,
          executed_action: body.executed_action,
          allow_r2_real_write_pilot: body.allow_r2_real_write_pilot,
          allow_generic_real_odoo_writes: body.allow_generic_real_odoo_writes,
          policy_passed: body.policy_passed,
          result: body.result,
        });
        r2Message.textContent = `R2 run: ${body.status} / action: ${body.executed_action}`;
      } catch (error) { r2RunOutput.textContent = `Execute failed: ${String(error)}`; }
    });

    document.getElementById("r2GetRun").addEventListener("click", async () => {
      if (!r2State.runId) { r2Message.textContent = "Execute R2 pilot first."; return; }
      try {
        const response = await fetch(`/v1/product/r2-write-pilot/runs/${r2State.runId}`);
        const body = await response.json();
        r2RunOutput.textContent = jsonText(body);
        r2Message.textContent = `Run ${body.run_id}: ${body.status}`;
      } catch (error) { r2RunOutput.textContent = `Get run failed: ${String(error)}`; }
    });

    document.getElementById("r2GetEvidence").addEventListener("click", async () => {
      if (!r2State.runId) { r2Message.textContent = "Execute R2 pilot first."; return; }
      r2Message.textContent = `Loading R2 evidence for run ${r2State.runId}...`;
      try {
        const response = await fetch(`/v1/product/r2-write-pilot/runs/${r2State.runId}/evidence`);
        const body = await response.json();
        r2EvidenceOutput.textContent = jsonText(Array.isArray(body) ? body.map(ev => ({
          evidence_id: ev.evidence_id,
          action_taken: ev.action_taken,
          pre_snapshot: ev.pre_snapshot,
          post_snapshot: ev.post_snapshot,
          rollback_instructions: ev.rollback_instructions,
          allow_r2_real_write_pilot: ev.allow_r2_real_write_pilot,
        })) : body);
        r2Message.textContent = `${Array.isArray(body) ? body.length : 0} evidence record(s) — rollback plan included.`;
      } catch (error) { r2EvidenceOutput.textContent = `Evidence failed: ${String(error)}`; }
    });

    document.getElementById("r2History").addEventListener("click", async () => {
      const skillId = getR2SkillId();
      if (!skillId) { r2Message.textContent = "Enter a skill id first."; return; }
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/r2-write-pilot/history`);
        const body = await response.json();
        r2HistoryOutput.textContent = jsonText(Array.isArray(body) ? body.map(r => ({
          request_id: r.request_id,
          status: r.status,
          target_model: r.target_model,
          target_record_id: r.target_record_id,
          target_fields: r.target_fields,
          environment: r.environment,
          allow_r2_real_write_pilot: r.allow_r2_real_write_pilot,
        })) : body);
        r2Message.textContent = `${Array.isArray(body) ? body.length : 0} R2 request(s) for skill.`;
      } catch (error) { r2HistoryOutput.textContent = `History failed: ${String(error)}`; }
    });

    // Sprint 10A — End-to-End Operator Flow
    const ofMessage = document.getElementById("ofMessage");
    const ofSessionOutput = document.getElementById("of-session-output");
    const ofRunOutput = document.getElementById("of-run-output");
    const ofTimelineOutput = document.getElementById("of-timeline-output");
    const ofSummaryOutput = document.getElementById("of-summary-output");
    const ofConnectionIdInput = document.getElementById("ofConnectionId");
    const ofState = { sessionId: null };

    const renderOfSession = (body) => {
      ofSessionOutput.textContent = jsonText({
        session_id: body.session_id,
        current_step: body.current_step,
        status: body.status,
        tenant_id: body.tenant_id,
        connection_id: body.connection_id,
        known_ids: body.known_ids || {},
      });
    };

    document.getElementById("ofCreateSession").addEventListener("click", async () => {
      ofMessage.textContent = "Creating operator session...";
      try {
        const response = await fetch("/v1/product/operator-sessions", { method: "POST" });
        const body = await response.json();
        if (!response.ok) { ofSessionOutput.textContent = `Create failed: ${body?.error?.message || "unknown"}`; return; }
        ofState.sessionId = body.session_id;
        renderOfSession(body);
        ofMessage.textContent = `Session created: ${body.session_id} — current step: ${body.current_step}`;
      } catch (error) { ofSessionOutput.textContent = `Create failed: ${String(error)}`; }
    });

    document.getElementById("ofSelectConnection").addEventListener("click", async () => {
      if (!ofState.sessionId) { ofMessage.textContent = "Create a session first."; return; }
      const connectionId = ofConnectionIdInput?.value?.trim();
      if (!connectionId) { ofMessage.textContent = "Enter a connection ID first."; return; }
      ofMessage.textContent = `Selecting connection ${connectionId}...`;
      try {
        const response = await fetch(`/v1/product/operator-sessions/${ofState.sessionId}/select-connection`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ connection_id: connectionId }),
        });
        const body = await response.json();
        if (!response.ok) { ofSessionOutput.textContent = `Select failed: ${body?.error?.message || "unknown"}`; return; }
        renderOfSession(body);
        ofMessage.textContent = `Connection selected: ${connectionId} — step: ${body.current_step}`;
      } catch (error) { ofSessionOutput.textContent = `Select failed: ${String(error)}`; }
    });

    document.getElementById("ofRunNext").addEventListener("click", async () => {
      if (!ofState.sessionId) { ofMessage.textContent = "Create a session first."; return; }
      ofMessage.textContent = `Running next step for ${ofState.sessionId}...`;
      try {
        const response = await fetch(`/v1/product/operator-sessions/${ofState.sessionId}/run-next`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) { ofRunOutput.textContent = `Run next failed: ${body?.error?.message || "unknown"}`; return; }
        renderOfSession(body);
        ofRunOutput.textContent = jsonText({
          step_status: body.step_status,
          message: body.message,
          current_step: body.current_step,
          known_ids: body.known_ids || {},
        });
        ofMessage.textContent = `Step: ${body.step_status} — ${body.message || "ok"} — now at: ${body.current_step}`;
      } catch (error) { ofRunOutput.textContent = `Run next failed: ${String(error)}`; }
    });

    document.getElementById("ofRunSafeReadonly").addEventListener("click", async () => {
      if (!ofState.sessionId) { ofMessage.textContent = "Create a session first."; return; }
      ofMessage.textContent = `Running full safe read-only path for ${ofState.sessionId}...`;
      try {
        const response = await fetch(`/v1/product/operator-sessions/${ofState.sessionId}/run-safe-readonly-path`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) { ofRunOutput.textContent = `Run path failed: ${body?.error?.message || "unknown"}`; return; }
        renderOfSession(body);
        ofRunOutput.textContent = jsonText({
          steps_executed: body.steps_executed || [],
          errors: body.errors || [],
          current_step: body.current_step,
          known_ids: body.known_ids || {},
        });
        const count = (body.steps_executed || []).length;
        ofMessage.textContent = `Safe path: ${count} step(s) executed — now at: ${body.current_step}`;
      } catch (error) { ofRunOutput.textContent = `Run path failed: ${String(error)}`; }
    });

    document.getElementById("ofTimeline").addEventListener("click", async () => {
      if (!ofState.sessionId) { ofMessage.textContent = "Create a session first."; return; }
      ofMessage.textContent = `Loading timeline for ${ofState.sessionId}...`;
      try {
        const response = await fetch(`/v1/product/operator-sessions/${ofState.sessionId}/timeline`);
        const body = await response.json();
        if (!response.ok) { ofTimelineOutput.textContent = `Timeline failed: ${body?.error?.message || "unknown"}`; return; }
        ofTimelineOutput.textContent = jsonText({
          current_step: body.current_step,
          steps_completed: body.steps_completed || [],
          steps_errored: body.steps_errored || [],
          events: (body.events || []).map(ev => ({ step: ev.step, status: ev.status, message: ev.detail?.message || ev.detail?.error || "" })),
        });
        ofMessage.textContent = `Timeline: ${(body.steps_completed || []).length} completed, ${(body.steps_errored || []).length} errored.`;
      } catch (error) { ofTimelineOutput.textContent = `Timeline failed: ${String(error)}`; }
    });

    document.getElementById("ofSummary").addEventListener("click", async () => {
      if (!ofState.sessionId) { ofMessage.textContent = "Create a session first."; return; }
      ofMessage.textContent = `Loading summary for ${ofState.sessionId}...`;
      try {
        const response = await fetch(`/v1/product/operator-sessions/${ofState.sessionId}/summary`);
        const body = await response.json();
        if (!response.ok) { ofSummaryOutput.textContent = `Summary failed: ${body?.error?.message || "unknown"}`; return; }
        ofSummaryOutput.textContent = jsonText({
          status: body.status,
          current_step: body.current_step,
          progress_pct: body.progress_pct,
          steps_completed: body.steps_completed,
          steps_total: body.steps_total,
          known_ids: body.known_ids || {},
          safety_invariants: body.safety_invariants || {},
        });
        ofMessage.textContent = `Summary: ${body.progress_pct}% complete — ${body.steps_completed}/${body.steps_total} steps — ${body.current_step}`;
      } catch (error) { ofSummaryOutput.textContent = `Summary failed: ${String(error)}`; }
    });

    // Sprint 9 — Production Safety & Tenant Controls
    const psaTenantNameInput = document.getElementById("psaTenantName");
    const psaMessage = document.getElementById("psaMessage");
    const psaTenantOutput = document.getElementById("psa-tenant-output");
    const psaSummaryOutput = document.getElementById("psa-summary-output");
    const psaKillSwitchOutput = document.getElementById("psa-kill-switch-output");
    const psaAuditExportOutput = document.getElementById("psa-audit-export-output");
    const psaPolicyOutput = document.getElementById("psa-policy-output");
    const psaRuntimeOutput = document.getElementById("psa-runtime-output");
    const psaState = { tenantId: null, exportId: null };

    document.getElementById("psaCreateTenant").addEventListener("click", async () => {
      const name = psaTenantNameInput?.value?.trim() || "Demo Tenant";
      psaMessage.textContent = `Creating tenant '${name}'...`;
      try {
        const response = await fetch("/v1/platform/tenants", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, environment: "staging" }),
        });
        const body = await response.json();
        if (!response.ok) { psaTenantOutput.textContent = `Create failed: ${body?.error?.message || "unknown"}`; return; }
        psaState.tenantId = body.tenant_id;
        psaTenantOutput.textContent = jsonText({
          tenant_id: body.tenant_id,
          name: body.name,
          environment: body.environment,
          status: body.status,
          kill_switches: body.kill_switches,
          secret_redaction_enforced: body.secret_redaction_enforced,
          roles: (body.roles || []).map(r => r.name),
        });
        psaMessage.textContent = `Tenant created: ${body.tenant_id}`;
      } catch (error) { psaTenantOutput.textContent = `Create failed: ${String(error)}`; }
    });

    document.getElementById("psaGetSafetySummary").addEventListener("click", async () => {
      if (!psaState.tenantId) { psaMessage.textContent = "Create a tenant first."; return; }
      psaMessage.textContent = `Loading safety summary for ${psaState.tenantId}...`;
      try {
        const response = await fetch(`/v1/platform/tenants/${psaState.tenantId}/safety-summary`);
        const body = await response.json();
        if (!response.ok) { psaSummaryOutput.textContent = `Summary failed: ${body?.error?.message || "unknown"}`; return; }
        psaSummaryOutput.textContent = jsonText({
          tenant_id: body.tenant_id,
          tenant_name: body.tenant_name,
          status: body.status,
          any_kill_switch_active: body.any_kill_switch_active,
          kill_switches: body.kill_switches,
          allow_generic_real_odoo_writes: body.allow_generic_real_odoo_writes,
          allow_r3_r4_real_writes: body.allow_r3_r4_real_writes,
          secret_redaction_enforced: body.secret_redaction_enforced,
          recent_kill_switch_events: body.recent_kill_switch_events,
        });
        psaMessage.textContent = `Safety summary loaded. Any kill switch active: ${body.any_kill_switch_active}`;
      } catch (error) { psaSummaryOutput.textContent = `Summary failed: ${String(error)}`; }
    });

    document.getElementById("psaActivateKillSwitch").addEventListener("click", async () => {
      if (!psaState.tenantId) { psaMessage.textContent = "Create a tenant first."; return; }
      psaMessage.textContent = `Activating write_pilot_kill_switch for ${psaState.tenantId}...`;
      try {
        const response = await fetch(`/v1/platform/tenants/${psaState.tenantId}/kill-switch`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            switch_name: "write_pilot_kill_switch",
            action: "activate",
            activated_by: { type: "user", id: "demo_admin", display_name: "Demo Admin" },
            reason: "Sprint 9 safety demo: activating write pilot kill switch.",
          }),
        });
        const body = await response.json();
        if (!response.ok) { psaKillSwitchOutput.textContent = `Kill switch failed: ${body?.error?.message || "unknown"}`; return; }
        psaKillSwitchOutput.textContent = jsonText({
          event_id: body.event_id,
          switch_name: body.switch_name,
          action: body.action,
          activated_by: body.activated_by,
          reason: body.reason,
        });
        psaMessage.textContent = `Kill switch activated: ${body.switch_name}`;
      } catch (error) { psaKillSwitchOutput.textContent = `Kill switch failed: ${String(error)}`; }
    });

    document.getElementById("psaDeactivateKillSwitch").addEventListener("click", async () => {
      if (!psaState.tenantId) { psaMessage.textContent = "Create a tenant first."; return; }
      psaMessage.textContent = `Deactivating write_pilot_kill_switch for ${psaState.tenantId}...`;
      try {
        const response = await fetch(`/v1/platform/tenants/${psaState.tenantId}/kill-switch`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            switch_name: "write_pilot_kill_switch",
            action: "deactivate",
            activated_by: { type: "user", id: "demo_admin", display_name: "Demo Admin" },
            reason: "Sprint 9 safety demo: deactivating write pilot kill switch.",
          }),
        });
        const body = await response.json();
        if (!response.ok) { psaKillSwitchOutput.textContent = `Kill switch failed: ${body?.error?.message || "unknown"}`; return; }
        psaKillSwitchOutput.textContent = jsonText({
          event_id: body.event_id,
          switch_name: body.switch_name,
          action: body.action,
        });
        psaMessage.textContent = `Kill switch deactivated: ${body.switch_name}`;
      } catch (error) { psaKillSwitchOutput.textContent = `Kill switch failed: ${String(error)}`; }
    });

    document.getElementById("psaGenerateAuditExport").addEventListener("click", async () => {
      if (!psaState.tenantId) { psaMessage.textContent = "Create a tenant first."; return; }
      psaMessage.textContent = `Generating audit export for ${psaState.tenantId}...`;
      try {
        const response = await fetch(`/v1/platform/tenants/${psaState.tenantId}/audit-export`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filters: {} }),
        });
        const body = await response.json();
        if (!response.ok) { psaAuditExportOutput.textContent = `Export failed: ${body?.error?.message || "unknown"}`; return; }
        psaState.exportId = body.export_id;
        psaAuditExportOutput.textContent = jsonText({
          export_id: body.export_id,
          tenant_id: body.tenant_id,
          export_type: body.export_type,
          record_count: body.record_count,
          status: body.status,
          result_preview: (body.result || []).slice(0, 3),
        });
        psaMessage.textContent = `Audit export generated: ${body.record_count} records, secrets redacted.`;
      } catch (error) { psaAuditExportOutput.textContent = `Export failed: ${String(error)}`; }
    });

    document.getElementById("psaEvaluatePolicy").addEventListener("click", async () => {
      if (!psaState.tenantId) { psaMessage.textContent = "Create a tenant first."; return; }
      psaMessage.textContent = `Evaluating operator policy for ${psaState.tenantId}...`;
      try {
        const response = await fetch("/v1/platform/policy/evaluate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            actor: { type: "user", id: "demo_operator", display_name: "Demo Operator", role: "operator" },
            action: "execute_real_read",
            resource: `tenant:${psaState.tenantId}`,
            context: {},
            tenant_id: psaState.tenantId,
          }),
        });
        const body = await response.json();
        if (!response.ok) { psaPolicyOutput.textContent = `Policy failed: ${body?.error?.message || "unknown"}`; return; }
        psaPolicyOutput.textContent = jsonText({
          allowed: body.allowed,
          actor: body.actor,
          action: body.action,
          reason: body.reason,
          violations: body.violations || [],
          kill_switches_active: body.kill_switches_active || [],
          allow_generic_real_odoo_writes: body.allow_generic_real_odoo_writes,
          allow_r3_r4_real_writes: body.allow_r3_r4_real_writes,
        });
        psaMessage.textContent = `Policy: ${body.allowed ? "ALLOWED" : "BLOCKED — " + body.reason}`;
      } catch (error) { psaPolicyOutput.textContent = `Policy failed: ${String(error)}`; }
    });

    document.getElementById("psaGetRuntimeSafety").addEventListener("click", async () => {
      psaMessage.textContent = "Loading platform runtime safety...";
      try {
        const response = await fetch("/v1/platform/runtime-safety");
        const body = await response.json();
        if (!response.ok) { psaRuntimeOutput.textContent = `Runtime safety failed: ${body?.error?.message || "unknown"}`; return; }
        psaRuntimeOutput.textContent = jsonText({
          safety_level: body.safety_level,
          platform_global_kill_switch: body.platform_global_kill_switch,
          runtime_execution_kill_switch: body.runtime_execution_kill_switch,
          write_pilot_kill_switch: body.write_pilot_kill_switch,
          allow_generic_real_odoo_writes: body.allow_generic_real_odoo_writes,
          allow_r3_r4_real_writes: body.allow_r3_r4_real_writes,
          allow_r1_real_write_pilot: body.allow_r1_real_write_pilot,
          secret_redaction_enforced: body.secret_redaction_enforced,
          active_tenant_count: body.active_tenant_count,
          recent_write_pilot_runs: body.recent_write_pilot_runs,
        });
        psaMessage.textContent = `Runtime safety level: ${body.safety_level}. Writes: BLOCKED.`;
      } catch (error) { psaRuntimeOutput.textContent = `Runtime safety failed: ${String(error)}`; }
    });

    // Sprint 8 — First Real Write Pilot (mail.message.create only)
    const wpSkillIdInput = document.getElementById("wpSkillId");
    const wpMessage = document.getElementById("wpMessage");
    const wpRequestOutput = document.getElementById("wp-request-output");
    const wpPolicyOutput = document.getElementById("wp-policy-output");
    const wpRunOutput = document.getElementById("wp-run-output");
    const wpEvidenceOutput = document.getElementById("wp-evidence-output");
    const wpHistoryOutput = document.getElementById("wp-history-output");
    const wpState = { requestId: null, runId: null };

    const getWpSkillId = () => wpSkillIdInput?.value?.trim() || "";

    document.getElementById("wpCreateRequest").addEventListener("click", async () => {
      const skillId = getWpSkillId();
      if (!skillId) { wpMessage.textContent = "Enter a skill id first."; return; }
      wpMessage.textContent = `Creating write pilot request for ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/write-pilot/request`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            requested_by: { type: "user", id: "demo_operator", display_name: "Demo Operator" },
            approver_1: { type: "user", id: "approver_1", display_name: "Demo Approver 1" },
            approver_2: { type: "user", id: "approver_2", display_name: "Demo Approver 2" },
            target_res_model: "sale.order",
            target_res_id: 42,
            payload: { body: "<p>ERPGuard Sprint 8 pilot audit note — controlled write test.</p>" },
          }),
        });
        const body = await response.json();
        if (!response.ok && response.status !== 200 && response.status !== 201) {
          wpRequestOutput.textContent = `Request failed: ${body?.error?.message || "unknown"}`;
          return;
        }
        wpState.requestId = body.request_id;
        wpRequestOutput.textContent = jsonText({
          request_id: body.request_id,
          target_model: body.target_model,
          target_res_model: body.target_res_model,
          status: body.status,
          allow_r1_real_write_pilot: body.allow_r1_real_write_pilot,
          allow_generic_real_odoo_writes: body.allow_generic_real_odoo_writes,
          idempotency_key: body.idempotency_key,
          duplicate: body._idempotent_duplicate || false,
        });
        wpMessage.textContent = `Pilot request: ${body.request_id} (target: ${body.target_model})`;
      } catch (error) { wpRequestOutput.textContent = `Request failed: ${String(error)}`; }
    });

    document.getElementById("wpCheckPolicy").addEventListener("click", async () => {
      if (!wpState.requestId) { wpMessage.textContent = "Create a pilot request first."; return; }
      wpMessage.textContent = `Checking pilot policy for ${wpState.requestId}...`;
      try {
        const response = await fetch(`/v1/product/write-pilot/requests/${wpState.requestId}/policy-check`, { method: "POST" });
        const body = await response.json();
        wpPolicyOutput.textContent = jsonText({
          passed: body.passed,
          allow_r1_real_write_pilot: body.allow_r1_real_write_pilot,
          allow_generic_real_odoo_writes: body.allow_generic_real_odoo_writes,
          allow_r3_r4_real_writes: body.allow_r3_r4_real_writes,
          target_model: body.target_model,
          target_whitelisted: body.target_whitelisted,
          violations: body.violations || [],
        });
        wpMessage.textContent = `Policy: ${body.passed ? "PASSED" : "BLOCKED (" + (body.violations || []).length + " violation(s))"}`;
      } catch (error) { wpPolicyOutput.textContent = `Policy check failed: ${String(error)}`; }
    });

    document.getElementById("wpExecute").addEventListener("click", async () => {
      if (!wpState.requestId) { wpMessage.textContent = "Create a pilot request first."; return; }
      wpMessage.textContent = `Executing pilot for request ${wpState.requestId}...`;
      try {
        const response = await fetch(`/v1/product/write-pilot/requests/${wpState.requestId}/execute`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) { wpRunOutput.textContent = `Execute failed: ${body?.error?.message || "unknown"}`; return; }
        wpState.runId = body.run_id;
        wpRunOutput.textContent = jsonText({
          run_id: body.run_id,
          status: body.status,
          executed_action: body.executed_action,
          allow_r1_real_write_pilot: body.allow_r1_real_write_pilot,
          allow_generic_real_odoo_writes: body.allow_generic_real_odoo_writes,
          policy_passed: body.policy_passed,
          result: body.result,
        });
        wpMessage.textContent = `Pilot run: ${body.status} / action: ${body.executed_action}`;
      } catch (error) { wpRunOutput.textContent = `Execute failed: ${String(error)}`; }
    });

    document.getElementById("wpGetRun").addEventListener("click", async () => {
      if (!wpState.runId) { wpMessage.textContent = "Execute pilot first."; return; }
      try {
        const response = await fetch(`/v1/product/write-pilot/runs/${wpState.runId}`);
        const body = await response.json();
        wpRunOutput.textContent = jsonText(body);
        wpMessage.textContent = `Run ${body.run_id}: ${body.status}`;
      } catch (error) { wpRunOutput.textContent = `Get run failed: ${String(error)}`; }
    });

    document.getElementById("wpGetEvidence").addEventListener("click", async () => {
      if (!wpState.runId) { wpMessage.textContent = "Execute pilot first."; return; }
      wpMessage.textContent = `Loading pilot evidence for run ${wpState.runId}...`;
      try {
        const response = await fetch(`/v1/product/write-pilot/runs/${wpState.runId}/evidence`);
        const body = await response.json();
        wpEvidenceOutput.textContent = jsonText(body);
        wpMessage.textContent = `${Array.isArray(body) ? body.length : 0} evidence record(s) for pilot run.`;
      } catch (error) { wpEvidenceOutput.textContent = `Evidence failed: ${String(error)}`; }
    });

    document.getElementById("wpHistory").addEventListener("click", async () => {
      const skillId = getWpSkillId();
      if (!skillId) { wpMessage.textContent = "Enter a skill id first."; return; }
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/write-pilot/history`);
        const body = await response.json();
        wpHistoryOutput.textContent = jsonText(Array.isArray(body) ? body.map(r => ({
          request_id: r.request_id,
          status: r.status,
          target_model: r.target_model,
          allow_r1_real_write_pilot: r.allow_r1_real_write_pilot,
        })) : body);
        wpMessage.textContent = `${Array.isArray(body) ? body.length : 0} pilot request(s) for skill.`;
      } catch (error) { wpHistoryOutput.textContent = `History failed: ${String(error)}`; }
    });

    // Sprint 7 — Write Capability Readiness & Risk Certification
    const wrSkillIdInput = document.getElementById("wrSkillId");
    const wrMessage = document.getElementById("wrMessage");
    const wrAssessmentOutput = document.getElementById("wr-assessment-output");
    const wrSummaryOutput = document.getElementById("wr-summary-output");
    const wrImpactOutput = document.getElementById("wr-impact-output");
    const wrRollbackOutput = document.getElementById("wr-rollback-output");
    const wrCertOutput = document.getElementById("wr-certification-output");
    const wrState = { assessmentId: null };

    const getWrSkillId = () => wrSkillIdInput?.value?.trim() || "";

    document.getElementById("wrRunAssessment").addEventListener("click", async () => {
      const skillId = getWrSkillId();
      if (!skillId) { wrMessage.textContent = "Enter a skill id first."; return; }
      wrMessage.textContent = `Running write readiness assessment for ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/write-readiness-assessment`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) { wrAssessmentOutput.textContent = `Assessment failed: ${body?.error?.message || "unknown"}`; return; }
        wrState.assessmentId = body.assessment_id;
        wrAssessmentOutput.textContent = jsonText({
          assessment_id: body.assessment_id,
          skill_id: body.skill_id,
          status: body.status,
          overall_risk_level: body.overall_risk_level,
          can_certify_write_readiness: body.can_certify_write_readiness,
          write_candidates_count: (body.write_candidates || []).length,
          blocking_issues: body.blocking_issues || [],
          can_execute_real_writes: body.can_execute_real_writes,
          real_erp_writes_enabled: body.real_erp_writes_enabled,
        });
        wrMessage.textContent = `Assessment completed. Risk level: ${body.overall_risk_level}. Can certify: ${body.can_certify_write_readiness}`;
      } catch (error) { wrAssessmentOutput.textContent = `Assessment failed: ${String(error)}`; }
    });

    document.getElementById("wrGetSummary").addEventListener("click", async () => {
      const skillId = getWrSkillId();
      if (!skillId) { wrMessage.textContent = "Enter a skill id first."; return; }
      wrMessage.textContent = `Loading write readiness summary for ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/write-readiness-summary`);
        const body = await response.json();
        wrSummaryOutput.textContent = jsonText({
          skill_id: body.skill_id,
          has_assessment: body.has_assessment,
          has_impact_preview: body.has_impact_preview,
          has_rollback_plan: body.has_rollback_plan,
          has_certification: body.has_certification,
          overall_risk_level: body.overall_risk_level,
          certification_status: body.certification_status,
          can_execute_real_writes: body.can_execute_real_writes,
          approved_for_real_execution: body.approved_for_real_execution,
        });
        wrMessage.textContent = `Summary loaded. Assessment: ${body.has_assessment}, Cert: ${body.has_certification}`;
      } catch (error) { wrSummaryOutput.textContent = `Summary failed: ${String(error)}`; }
    });

    document.getElementById("wrGenerateImpact").addEventListener("click", async () => {
      if (!wrState.assessmentId) { wrMessage.textContent = "Run assessment first."; return; }
      wrMessage.textContent = `Generating impact preview for assessment ${wrState.assessmentId}...`;
      try {
        const response = await fetch(`/v1/product/write-readiness-assessments/${wrState.assessmentId}/impact-preview`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) { wrImpactOutput.textContent = `Impact failed: ${body?.error?.message || "unknown"}`; return; }
        wrImpactOutput.textContent = jsonText({
          impact_id: body.impact_id,
          assessment_id: body.assessment_id,
          impact_summary: body.impact_summary,
          affected_models: body.affected_models,
          estimated_record_count: body.estimated_record_count,
          reversible: body.reversible,
          can_execute_real_writes: body.can_execute_real_writes,
        });
        wrMessage.textContent = `Impact preview: ${body.estimated_record_count} estimated records, reversible=${body.reversible}`;
      } catch (error) { wrImpactOutput.textContent = `Impact failed: ${String(error)}`; }
    });

    document.getElementById("wrDraftRollback").addEventListener("click", async () => {
      if (!wrState.assessmentId) { wrMessage.textContent = "Run assessment first."; return; }
      wrMessage.textContent = `Drafting rollback plan for assessment ${wrState.assessmentId}...`;
      try {
        const response = await fetch(`/v1/product/write-readiness-assessments/${wrState.assessmentId}/rollback-plan`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) { wrRollbackOutput.textContent = `Rollback failed: ${body?.error?.message || "unknown"}`; return; }
        wrRollbackOutput.textContent = jsonText({
          plan_id: body.plan_id,
          assessment_id: body.assessment_id,
          rollback_steps: body.rollback_steps,
          backup_strategy: body.backup_strategy,
          estimated_rollback_time_minutes: body.estimated_rollback_time_minutes,
          can_execute_real_writes: body.can_execute_real_writes,
        });
        wrMessage.textContent = `Rollback plan drafted: ${(body.rollback_steps || []).length} steps, ~${body.estimated_rollback_time_minutes}min`;
      } catch (error) { wrRollbackOutput.textContent = `Rollback failed: ${String(error)}`; }
    });

    document.getElementById("wrCertify").addEventListener("click", async () => {
      const skillId = getWrSkillId();
      if (!skillId) { wrMessage.textContent = "Enter a skill id first."; return; }
      wrMessage.textContent = `Certifying write readiness for ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/write-readiness-certification`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) { wrCertOutput.textContent = `Certification failed: ${body?.error?.message || "unknown"}`; return; }
        wrCertOutput.textContent = jsonText({
          certification_id: body.certification_id,
          skill_id: body.skill_id,
          certification_status: body.certification_status,
          overall_risk_level: body.overall_risk_level,
          dual_approval_required: body.dual_approval_required,
          can_certify_real_execution: body.can_certify_real_execution,
          can_execute_real_writes: body.can_execute_real_writes,
          approved_for_real_execution: body.approved_for_real_execution,
        });
        wrMessage.textContent = `Certification issued: ${body.certification_status} (risk: ${body.overall_risk_level}). Writes: BLOCKED.`;
      } catch (error) { wrCertOutput.textContent = `Certification failed: ${String(error)}`; }
    });

    // Sprint 6 — Controlled Real Read Execution & Live Evidence
    const lrSkillIdInput = document.getElementById("lrSkillId");
    const lrMessage = document.getElementById("lrMessage");
    const lrConnectionContext = document.getElementById("lrConnectionContext");
    const lrPolicyOutput = document.getElementById("lrPolicyOutput");
    const lrRequestOutput = document.getElementById("lrRequestOutput");
    const lrRunOutput = document.getElementById("lrRunOutput");
    const lrEvidenceOutput = document.getElementById("lrEvidenceOutput");

    const getLrSkillId = () => lrSkillIdInput?.value?.trim() || "";
    const lrState = { requestId: null, runId: null };

    document.getElementById("lrCheckContext").addEventListener("click", async () => {
      const skillId = getLrSkillId();
      if (!skillId) { lrMessage.textContent = "Enter a skill id first."; return; }
      lrMessage.textContent = `Checking connection context for ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/connection-context`);
        const body = await response.json();
        lrConnectionContext.textContent = jsonText({
          connection_id: body.connection_id,
          erp_type: body.erp_type,
          connection_status: body.connection_status,
          url: body.url,
          database: body.database,
          username: body.username,
          has_credentials: body.has_credentials,
          secrets_redacted: body.secrets_redacted,
          resolved: body.resolved,
          missing_reason: body.missing_reason || null,
        });
        lrMessage.textContent = body.resolved ? `Connection resolved: ${body.connection_id}` : `Connection missing: ${body.missing_reason || "unknown"}`;
      } catch (error) {
        lrConnectionContext.textContent = `Context check failed: ${String(error)}`;
      }
    });

    document.getElementById("lrCheckPolicy").addEventListener("click", async () => {
      const skillId = getLrSkillId();
      if (!skillId) { lrMessage.textContent = "Enter a skill id first."; return; }
      lrMessage.textContent = `Checking live read policy for ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/live-read-policy`);
        const body = await response.json();
        lrPolicyOutput.textContent = jsonText({
          passed: body.passed,
          allow_real_odoo_reads: body.allow_real_odoo_reads,
          allow_live_read_evidence: body.allow_live_read_evidence,
          can_execute_real_writes: body.can_execute_real_writes,
          real_erp_writes_enabled: body.real_erp_writes_enabled,
          violations: body.violations || [],
        });
        lrMessage.textContent = `Live read policy: ${body.passed ? "passed" : "blocked (" + (body.violations || []).length + " violation(s))"}`;
      } catch (error) {
        lrPolicyOutput.textContent = `Policy check failed: ${String(error)}`;
      }
    });

    document.getElementById("lrCreateRequest").addEventListener("click", async () => {
      const skillId = getLrSkillId();
      if (!skillId) { lrMessage.textContent = "Enter a skill id first."; return; }
      lrMessage.textContent = `Creating live read request for ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/live-read-execution-request`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            requested_by: { type: "user", id: "demo_operator", display_name: "Demo Operator" },
            inputs: { live_read: true },
          }),
        });
        const body = await response.json();
        if (!response.ok && response.status !== 200) {
          lrRequestOutput.textContent = `Request failed: ${body?.error?.message || "unknown error"}`;
          lrMessage.textContent = "Live read request failed.";
          return;
        }
        lrState.requestId = body.request_id;
        lrRequestOutput.textContent = jsonText({
          request_id: body.request_id,
          connection_id: body.connection_id,
          status: body.status,
          can_execute_real_writes: body.can_execute_real_writes,
          allow_real_odoo_reads: body.allow_real_odoo_reads,
          idempotency_key: body.idempotency_key,
          duplicate: body._idempotent_duplicate || false,
        });
        lrMessage.textContent = `Live read request: ${body.request_id}`;
      } catch (error) {
        lrRequestOutput.textContent = `Request failed: ${String(error)}`;
      }
    });

    document.getElementById("lrRunExecution").addEventListener("click", async () => {
      if (!lrState.requestId) {
        lrMessage.textContent = "Create a live read request first.";
        return;
      }
      lrMessage.textContent = `Running live read execution for request ${lrState.requestId}...`;
      try {
        const response = await fetch(`/v1/product/execution-requests/${lrState.requestId}/run-live-read`, {
          method: "POST",
        });
        const body = await response.json();
        if (!response.ok) {
          lrRunOutput.textContent = `Run failed: ${body?.error?.message || "unknown error"}`;
          lrMessage.textContent = "Live read execution failed.";
          return;
        }
        lrState.runId = body.run_id;
        lrRunOutput.textContent = jsonText({
          run_id: body.run_id,
          status: body.status,
          connection_id: body.connection_id,
          can_execute_real_writes: body.can_execute_real_writes,
          allow_real_odoo_reads: body.allow_real_odoo_reads,
          real_read_count: body.real_read_count,
          blocked_write_count: body.blocked_write_count,
          steps_total: body.plan?.total_steps || 0,
        });
        lrMessage.textContent = `Live read completed: ${body.real_read_count} real read(s), ${body.blocked_write_count} write(s) blocked.`;
      } catch (error) {
        lrRunOutput.textContent = `Run failed: ${String(error)}`;
      }
    });

    document.getElementById("lrGetEvidence").addEventListener("click", async () => {
      if (!lrState.runId) {
        lrMessage.textContent = "Run a live read execution first.";
        return;
      }
      lrMessage.textContent = `Loading live evidence for run ${lrState.runId}...`;
      try {
        const response = await fetch(`/v1/product/live-read-runs/${lrState.runId}/live-evidence`);
        const body = await response.json();
        if (!response.ok) {
          lrEvidenceOutput.textContent = `Evidence failed: ${body?.error?.message || "unknown error"}`;
          return;
        }
        lrEvidenceOutput.textContent = jsonText(body);
        lrMessage.textContent = `${Array.isArray(body) ? body.length : 0} live evidence record(s) — all reads, no writes.`;
      } catch (error) {
        lrEvidenceOutput.textContent = `Evidence failed: ${String(error)}`;
      }
    });

    // Sprint 5 — Execution Sandbox
    const sandboxSkillIdInput = document.getElementById("sandboxSkillId");
    const sandboxMessage = document.getElementById("sandboxMessage");
    const executionPolicyOutput = document.getElementById("executionPolicyOutput");
    const executionRequestOutput = document.getElementById("executionRequestOutput");
    const executionRunOutput = document.getElementById("executionRunOutput");
    const executionTimelineOutput = document.getElementById("executionTimelineOutput");
    const blockedWritesOutput = document.getElementById("blockedWritesOutput");

    const getSandboxSkillId = () => sandboxSkillIdInput?.value?.trim() || "";
    const sandboxState = { requestId: null, runId: null };

    document.getElementById("checkExecutionPolicy").addEventListener("click", async () => {
      const skillId = getSandboxSkillId();
      if (!skillId) { sandboxMessage.textContent = "Enter a skill id first."; return; }
      sandboxMessage.textContent = `Checking execution policy for ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/execution-policy`);
        const body = await response.json();
        executionPolicyOutput.textContent = jsonText({
          passed: body.passed,
          can_execute_real_writes: body.can_execute_real_writes,
          real_erp_writes_enabled: body.real_erp_writes_enabled,
          violations: body.violations || [],
        });
        sandboxMessage.textContent = `Policy check: ${body.passed ? "passed" : "blocked (" + (body.violations || []).length + " violation(s))"}`;
      } catch (error) {
        executionPolicyOutput.textContent = `Policy check failed: ${String(error)}`;
      }
    });

    document.getElementById("createExecutionRequest").addEventListener("click", async () => {
      const skillId = getSandboxSkillId();
      if (!skillId) { sandboxMessage.textContent = "Enter a skill id first."; return; }
      sandboxMessage.textContent = `Creating execution request for ${skillId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/execution-requests`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            requested_by: { type: "user", id: "demo_operator", display_name: "Demo Operator" },
            inputs: { dry_run: true },
          }),
        });
        const body = await response.json();
        if (!response.ok) {
          executionRequestOutput.textContent = `Request failed: ${body?.error?.message || "unknown error"}`;
          sandboxMessage.textContent = `Execution request failed.`;
          return;
        }
        sandboxState.requestId = body.request_id;
        executionRequestOutput.textContent = jsonText({
          request_id: body.request_id,
          status: body.status,
          can_execute_real_writes: body.can_execute_real_writes,
          real_erp_writes_enabled: body.real_erp_writes_enabled,
          idempotency_key: body.idempotency_key,
          duplicate: body._idempotent_duplicate || false,
        });
        sandboxMessage.textContent = `Execution request created: ${body.request_id}`;
      } catch (error) {
        executionRequestOutput.textContent = `Request failed: ${String(error)}`;
      }
    });

    document.getElementById("runExecution").addEventListener("click", async () => {
      const skillId = getSandboxSkillId();
      if (!skillId || !sandboxState.requestId) {
        sandboxMessage.textContent = "Create an execution request first.";
        return;
      }
      sandboxMessage.textContent = `Running dry-run execution for request ${sandboxState.requestId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/execution-requests/${sandboxState.requestId}/run`, {
          method: "POST",
        });
        const body = await response.json();
        if (!response.ok) {
          executionRunOutput.textContent = `Run failed: ${body?.error?.message || "unknown error"}`;
          sandboxMessage.textContent = `Execution run failed.`;
          return;
        }
        sandboxState.runId = body.run_id;
        executionRunOutput.textContent = jsonText({
          run_id: body.run_id,
          status: body.status,
          can_execute_real_writes: body.can_execute_real_writes,
          real_erp_writes_enabled: body.real_erp_writes_enabled,
          blocked_write_count: body.blocked_write_count,
          steps_total: body.plan?.total_steps || 0,
          blocked_write_candidates: body.plan?.blocked_write_candidates || 0,
        });
        sandboxMessage.textContent = `Dry-run completed: ${body.status}. Blocked writes: ${body.blocked_write_count}.`;
      } catch (error) {
        executionRunOutput.textContent = `Run failed: ${String(error)}`;
      }
    });

    document.getElementById("getExecutionTimeline").addEventListener("click", async () => {
      const skillId = getSandboxSkillId();
      if (!skillId || !sandboxState.runId) {
        sandboxMessage.textContent = "Run execution first.";
        return;
      }
      sandboxMessage.textContent = `Loading timeline for run ${sandboxState.runId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/execution-runs/${sandboxState.runId}/timeline`);
        const body = await response.json();
        if (!response.ok) {
          executionTimelineOutput.textContent = `Timeline failed: ${body?.error?.message || "unknown error"}`;
          return;
        }
        executionTimelineOutput.textContent = jsonText({
          run_id: body.run_id,
          total_steps: body.total_steps,
          can_execute_real_writes: body.can_execute_real_writes,
          real_erp_writes_enabled: body.real_erp_writes_enabled,
          steps: (body.steps || []).map((s) => ({ step_id: s.step_id, type: s.step_type, status: s.status })),
        });
        sandboxMessage.textContent = `Timeline: ${body.total_steps} step(s).`;
      } catch (error) {
        executionTimelineOutput.textContent = `Timeline failed: ${String(error)}`;
      }
    });

    document.getElementById("getBlockedWrites").addEventListener("click", async () => {
      const skillId = getSandboxSkillId();
      if (!skillId || !sandboxState.runId) {
        sandboxMessage.textContent = "Run execution first.";
        return;
      }
      sandboxMessage.textContent = `Loading blocked write evidence for run ${sandboxState.runId}...`;
      try {
        const response = await fetch(`/v1/product/skills/${skillId}/execution-runs/${sandboxState.runId}/blocked-writes`);
        const body = await response.json();
        if (!response.ok) {
          blockedWritesOutput.textContent = `Blocked writes failed: ${body?.error?.message || "unknown error"}`;
          return;
        }
        blockedWritesOutput.textContent = jsonText(body);
        sandboxMessage.textContent = `${Array.isArray(body) ? body.length : 0} blocked write(s) evidenced.`;
      } catch (error) {
        blockedWritesOutput.textContent = `Blocked writes failed: ${String(error)}`;
      }
    });

    loadLatestOdooConnectionButton.addEventListener("click", loadLatestOdooConnection);
    runBusinessAnalysisButton.addEventListener("click", runBusinessAnalysis);
    document.getElementById("loadMarketplaceConnectors").addEventListener("click", loadMarketplaceConnectors);
    document.getElementById("loadMarketplaceTemplates").addEventListener("click", loadMarketplaceTemplates);
    document.getElementById("checkMarketplaceRequirements").addEventListener("click", checkMarketplaceRequirements);
    document.getElementById("installMarketplaceDraft").addEventListener("click", installMarketplaceDraft);
    document.getElementById("loadMarketplaceInstalled").addEventListener("click", loadMarketplaceInstalled);
    document.getElementById("createAgentBuilderSession").addEventListener("click", createAgentBuilderSession);
    document.getElementById("loadAgentBuilderStepLibrary").addEventListener("click", loadAgentBuilderStepLibrary);
    document.getElementById("configureAgentBuilder").addEventListener("click", configureAgentBuilder);
    document.getElementById("previewAgentBuilder").addEventListener("click", previewAgentBuilder);
    document.getElementById("saveAgentBuilderDraft").addEventListener("click", saveAgentBuilderDraft);
    document.getElementById("loadConnectorScopes").addEventListener("click", loadConnectorScopes);
    document.getElementById("createConnectorAuthProfile").addEventListener("click", createConnectorAuthProfile);
    document.getElementById("testConnectorAuthProfile").addEventListener("click", testConnectorAuthProfile);
    document.getElementById("rotateConnectorAuthProfile").addEventListener("click", rotateConnectorAuthProfile);
    document.getElementById("revokeConnectorAuthProfile").addEventListener("click", revokeConnectorAuthProfile);
    document.getElementById("loadConnectorAuthAudit").addEventListener("click", loadConnectorAuthAudit);

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

    // Sprint 18 — External Connector Read-Only Pilot
    const extConnProfileIdInput = document.getElementById("extConnProfileId");
    const extConnPolicyOutput = document.getElementById("extConnPolicyOutput");
    const extConnReadinessOutput = document.getElementById("extConnReadinessOutput");
    const extConnCalendarsOutput = document.getElementById("extConnCalendarsOutput");
    const extConnEventsOutput = document.getElementById("extConnEventsOutput");
    const extConnEvidenceOutput = document.getElementById("extConnEvidenceOutput");
    const extConnSignalsOutput = document.getElementById("extConnSignalsOutput");
    const extConnAuditOutput = document.getElementById("extConnAuditOutput");

    const extConnState = { lastEvidenceId: null };

    document.getElementById("extConnPolicy").addEventListener("click", async () => {
      const r = await fetch("/v1/external-connectors/google-calendar-readonly/policy");
      extConnPolicyOutput.textContent = jsonText(await r.json());
    });

    document.getElementById("extConnTestReadiness").addEventListener("click", async () => {
      const profileId = extConnProfileIdInput.value.trim() || "demo_profile";
      const r = await fetch("/v1/external-connectors/google-calendar-readonly/test-readiness", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auth_profile_id: profileId, actor: { id: "demo_user" } }),
      });
      extConnReadinessOutput.textContent = jsonText(await r.json());
    });

    document.getElementById("extConnReadCalendars").addEventListener("click", async () => {
      const profileId = extConnProfileIdInput.value.trim() || "demo_profile";
      const r = await fetch("/v1/external-connectors/google-calendar-readonly/read-calendars", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auth_profile_id: profileId, actor: { id: "demo_user" } }),
      });
      const body = await r.json();
      if (body.evidence_id) extConnState.lastEvidenceId = body.evidence_id;
      extConnCalendarsOutput.textContent = jsonText(body);
    });

    document.getElementById("extConnReadEvents").addEventListener("click", async () => {
      const profileId = extConnProfileIdInput.value.trim() || "demo_profile";
      const r = await fetch("/v1/external-connectors/google-calendar-readonly/read-upcoming-events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auth_profile_id: profileId, max_results: 5, actor: { id: "demo_user" } }),
      });
      const body = await r.json();
      if (body.evidence_id) extConnState.lastEvidenceId = body.evidence_id;
      extConnEventsOutput.textContent = jsonText(body);
    });

    document.getElementById("extConnLoadEvidence").addEventListener("click", async () => {
      const profileId = extConnProfileIdInput.value.trim() || "demo_profile";
      if (extConnState.lastEvidenceId) {
        const r = await fetch(`/v1/external-connectors/read-evidence/${extConnState.lastEvidenceId}`);
        extConnEvidenceOutput.textContent = jsonText(await r.json());
      } else {
        const r = await fetch(`/v1/external-connectors/auth-profiles/${profileId}/read-evidence`);
        extConnEvidenceOutput.textContent = jsonText(await r.json());
      }
    });

    document.getElementById("extConnLoadSignals").addEventListener("click", async () => {
      const profileId = extConnProfileIdInput.value.trim() || "demo_profile";
      const r = await fetch(`/v1/external-connectors/auth-profiles/${profileId}/signals`);
      extConnSignalsOutput.textContent = jsonText(await r.json());
    });

    document.getElementById("extConnLoadAudit").addEventListener("click", async () => {
      const profileId = extConnProfileIdInput.value.trim() || "demo_profile";
      const r = await fetch(`/v1/external-connectors/auth-profiles/${profileId}/audit`);
      extConnAuditOutput.textContent = jsonText(await r.json());
    });

    // Sprint 19 — Google Calendar OAuth Authorization
    const oauthProfileIdInput = document.getElementById("oauthProfileId");
    const oauthRedirectUriInput = document.getElementById("oauthRedirectUri");
    const oauthStateTokenInput = document.getElementById("oauthStateToken");
    const oauthAuthorizeOutput = document.getElementById("oauthAuthorizeOutput");
    const oauthCallbackOutput = document.getElementById("oauthCallbackOutput");
    const oauthStatusOutput = document.getElementById("oauthStatusOutput");
    const oauthScopeOutput = document.getElementById("oauthScopeOutput");
    const oauthRevokeOutput = document.getElementById("oauthRevokeOutput");
    const oauthState = { lastStateToken: null };

    document.getElementById("oauthAuthorize").addEventListener("click", async () => {
      const profileId = oauthProfileIdInput.value.trim() || "demo_oauth_profile";
      const redirectUri = oauthRedirectUriInput.value.trim() || null;
      const r = await fetch("/v1/oauth/google-calendar/authorize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: profileId, redirect_uri: redirectUri, actor: { id: "demo_user" } }),
      });
      const body = await r.json();
      if (body.state_token) {
        oauthState.lastStateToken = body.state_token;
        oauthStateTokenInput.value = body.state_token;
      }
      oauthAuthorizeOutput.textContent = jsonText(body);
    });

    document.getElementById("oauthSimulateCallback").addEventListener("click", async () => {
      const stateToken = oauthStateTokenInput.value.trim() || oauthState.lastStateToken;
      if (!stateToken) {
        oauthCallbackOutput.textContent = "Generate an authorization URL first (Step 1).";
        return;
      }
      const r = await fetch(`/v1/oauth/google-calendar/callback?code=placeholder_code_demo&state=${encodeURIComponent(stateToken)}`);
      oauthCallbackOutput.textContent = jsonText(await r.json());
    });

    document.getElementById("oauthStatus").addEventListener("click", async () => {
      const profileId = oauthProfileIdInput.value.trim() || "demo_oauth_profile";
      const r = await fetch(`/v1/oauth/google-calendar/status/${profileId}`);
      oauthStatusOutput.textContent = jsonText(await r.json());
    });

    document.getElementById("oauthVerifyScope").addEventListener("click", async () => {
      const profileId = oauthProfileIdInput.value.trim() || "demo_oauth_profile";
      const r = await fetch(`/v1/oauth/google-calendar/verify-scope/${profileId}`);
      oauthScopeOutput.textContent = jsonText(await r.json());
    });

    document.getElementById("oauthRevoke").addEventListener("click", async () => {
      const profileId = oauthProfileIdInput.value.trim() || "demo_oauth_profile";
      const r = await fetch(`/v1/oauth/google-calendar/revoke/${profileId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor: { id: "demo_user" } }),
      });
      oauthRevokeOutput.textContent = jsonText(await r.json());
    });
  </script>
</body>
</html>"""
