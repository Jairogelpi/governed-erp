import { useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import { JsonBlock } from "../components/JsonBlock";
import { StatusBadge } from "../components/StatusBadge";

export function Runs() {
  // Plan
  const [connectionId, setConnectionId] = useState("");
  const [skillPackageId, setSkillPackageId] = useState("");
  const [capability, setCapability] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [capabilityPayloadJson, setCapabilityPayloadJson] = useState("{}");
  const [planError, setPlanError] = useState<string | null>(null);
  const [run, setRun] = useState<{ id: string; status: string } | null>(null);

  // Get / lifecycle
  const [runId, setRunId] = useState("");
  const [runDetail, setRunDetail] = useState<unknown>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [approvalIds, setApprovalIds] = useState("");
  const [evidence, setEvidence] = useState<unknown>(null);
  const [cleanupPlan, setCleanupPlan] = useState<unknown>(null);

  // Kill switch
  const [killSwitchError, setKillSwitchError] = useState<string | null>(null);
  const [killSwitchStatus, setKillSwitchStatus] = useState<string | null>(null);

  async function planRun() {
    setPlanError(null);
    setRun(null);
    let capabilityPayload;
    try {
      capabilityPayload = JSON.parse(capabilityPayloadJson);
    } catch {
      setPlanError("El JSON de payload de capacidad no es válido.");
      return;
    }
    const { data, error } = await api.POST("/v1/runs/plan", {
      body: {
        connection_id: connectionId,
        skill_package_id: skillPackageId || undefined,
        capability,
        idempotency_key: idempotencyKey,
        capability_payload: capabilityPayload,
      },
    });
    if (error) {
      setPlanError("No se pudo planificar la ejecución.");
      return;
    }
    setRun({ id: data.id, status: data.status });
    setRunId(data.id);
  }

  async function loadRun() {
    setRunError(null);
    setRunDetail(null);
    const { data, error } = await api.GET("/v1/runs/{run_id}", { params: { path: { run_id: runId } } });
    if (error) {
      setRunError("No se encontró la ejecución.");
      return;
    }
    setRunDetail(data);
  }

  async function approveRun() {
    setRunError(null);
    const { data, error } = await api.POST("/v1/runs/{run_id}/approve", {
      params: { path: { run_id: runId } },
      body: {
        approval_ids: approvalIds.split(",").map((item) => item.trim()).filter(Boolean),
        ttl_seconds: 900,
      },
    });
    if (error) {
      setRunError("No se pudo aprobar la ejecución.");
      return;
    }
    setRunDetail(data);
  }

  async function executeRun() {
    setRunError(null);
    const { data, error } = await api.POST("/v1/runs/{run_id}/execute", { params: { path: { run_id: runId } } });
    if (error) {
      setRunError("No se pudo ejecutar (el permiso puede estar expirado o incompleto).");
      return;
    }
    setRunDetail(data);
  }

  async function revokeRun() {
    setRunError(null);
    const { data, error } = await api.POST("/v1/runs/{run_id}/revoke", { params: { path: { run_id: runId } } });
    if (error) {
      setRunError("No se pudo revocar la ejecución.");
      return;
    }
    setRunDetail(data);
  }

  async function loadEvidence() {
    setRunError(null);
    const { data, error } = await api.GET("/v1/runs/{run_id}/evidence", { params: { path: { run_id: runId } } });
    if (error) {
      setRunError("La evidencia todavía no está disponible para esta ejecución.");
      return;
    }
    setEvidence(data);
  }

  async function loadCleanupPlan() {
    setRunError(null);
    const { data, error } = await api.GET("/v1/runs/{run_id}/cleanup-plan", { params: { path: { run_id: runId } } });
    if (error) {
      setRunError("No se pudo calcular el plan de limpieza.");
      return;
    }
    setCleanupPlan(data);
  }

  async function setKillSwitch(active: boolean) {
    setKillSwitchError(null);
    const { data, error } = await api.POST("/v1/runs/kill-switch", { body: { active } });
    if (error) {
      setKillSwitchError("No se pudo cambiar el interruptor de emergencia.");
      return;
    }
    setKillSwitchStatus(`active=${data.active} (${data.updated_at})`);
  }

  return (
    <div>
      <h2>Ejecuciones</h2>

      <div className="card">
        <h3>Planificar ejecución</h3>
        <label>
          Connection ID
          <br />
          <input value={connectionId} onChange={(event) => setConnectionId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Skill package ID
          <br />
          <input value={skillPackageId} onChange={(event) => setSkillPackageId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Capability
          <br />
          <input value={capability} onChange={(event) => setCapability(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Idempotency key
          <br />
          <input value={idempotencyKey} onChange={(event) => setIdempotencyKey(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Payload de capacidad (JSON)
          <br />
          <textarea value={capabilityPayloadJson} onChange={(event) => setCapabilityPayloadJson(event.target.value)} rows={3} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={planRun}>
            Planificar
          </button>
        </p>
        {planError && <ErrorState message={planError} />}
        {run && (
          <p>
            Run <strong>{run.id}</strong> -- <StatusBadge status={run.status} />
          </p>
        )}
      </div>

      <div className="card">
        <h3>Ciclo de vida de la ejecución</h3>
        <label>
          Run ID
          <br />
          <input value={runId} onChange={(event) => setRunId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Approval IDs (separados por coma)
          <br />
          <input value={approvalIds} onChange={(event) => setApprovalIds(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={loadRun}>
            Consultar
          </button>{" "}
          <button className="primary" onClick={approveRun}>
            Aprobar
          </button>{" "}
          <button className="primary" onClick={executeRun}>
            Ejecutar
          </button>{" "}
          <button className="primary" onClick={revokeRun}>
            Revocar
          </button>{" "}
          <button className="primary" onClick={loadEvidence}>
            Ver evidencia
          </button>{" "}
          <button className="primary" onClick={loadCleanupPlan}>
            Ver plan de limpieza
          </button>
        </p>
        {runError && <ErrorState message={runError} />}
        {runDetail !== null && <JsonBlock value={runDetail} />}
        {evidence !== null && (
          <>
            <h4>Evidencia</h4>
            <JsonBlock value={evidence} />
          </>
        )}
        {cleanupPlan !== null && (
          <>
            <h4>Plan de limpieza</h4>
            <JsonBlock value={cleanupPlan} />
          </>
        )}
      </div>

      <div className="card">
        <h3>Interruptor de emergencia (kill switch)</h3>
        <p>
          <button className="primary" onClick={() => setKillSwitch(true)}>
            Activar
          </button>{" "}
          <button className="primary" onClick={() => setKillSwitch(false)}>
            Desactivar
          </button>
        </p>
        {killSwitchError && <ErrorState message={killSwitchError} />}
        {killSwitchStatus && <p>{killSwitchStatus}</p>}
      </div>
    </div>
  );
}
