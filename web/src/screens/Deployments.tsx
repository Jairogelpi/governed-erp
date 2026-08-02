import { useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import { JsonBlock } from "../components/JsonBlock";
import { StatusBadge } from "../components/StatusBadge";

export function Deployments() {
  // Compile
  const [compileCandidateId, setCompileCandidateId] = useState("");
  const [connectorId, setConnectorId] = useState("");
  const [workflowStepsJson, setWorkflowStepsJson] = useState('[{"step_name": "create", "capability": "quote.create_draft"}]');
  const [compileError, setCompileError] = useState<string | null>(null);
  const [skillPackage, setSkillPackage] = useState<{ id: string; status: string } | null>(null);

  // Skill package lookup
  const [skillId, setSkillId] = useState("");
  const [versionId, setVersionId] = useState("");
  const [skillDetail, setSkillDetail] = useState<unknown>(null);
  const [skillError, setSkillError] = useState<string | null>(null);

  // Promote / rollback
  const [shadowDeploymentIdForPromotion, setShadowDeploymentIdForPromotion] = useState("");
  const [processKeyForRollback, setProcessKeyForRollback] = useState("");
  const [promoteError, setPromoteError] = useState<string | null>(null);
  const [promoteMessage, setPromoteMessage] = useState<string | null>(null);

  // Shadow deployment
  const [candidateId, setCandidateId] = useState("");
  const [proofId, setProofId] = useState("");
  const [objectType, setObjectType] = useState("sales_order");
  const [shadowError, setShadowError] = useState<string | null>(null);
  const [shadow, setShadow] = useState<{ id: string; status: string } | null>(null);
  const [deploymentId, setDeploymentId] = useState("");
  const [dashboard, setDashboard] = useState<unknown>(null);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  async function compile() {
    setCompileError(null);
    setSkillPackage(null);
    let workflowSteps;
    try {
      workflowSteps = JSON.parse(workflowStepsJson);
    } catch {
      setCompileError("El JSON de pasos de flujo no es válido.");
      return;
    }
    const { data, error } = await api.POST("/v1/process-candidates/{candidate_id}/compile", {
      params: { path: { candidate_id: compileCandidateId } },
      body: { connector_id: connectorId, workflow_steps: workflowSteps },
    });
    if (error) {
      setCompileError("No se pudo compilar el candidato.");
      return;
    }
    setSkillPackage({ id: data.id, status: data.status });
    setSkillId(data.id);
  }

  async function loadSkillPackage() {
    setSkillError(null);
    setSkillDetail(null);
    const { data, error } = await api.GET("/v1/skills/{skill_id}/versions/{version_id}", {
      params: { path: { skill_id: skillId, version_id: versionId } },
    });
    if (error) {
      setSkillError("No se encontró el paquete de skill.");
      return;
    }
    setSkillDetail(data);
  }

  async function approveSkillPackage() {
    setSkillError(null);
    const { data, error } = await api.POST("/v1/skills/{skill_id}/versions/{version_id}/approve", {
      params: { path: { skill_id: skillId, version_id: versionId } },
    });
    if (error) {
      setSkillError("No se pudo aprobar el paquete de skill.");
      return;
    }
    setSkillDetail(data);
  }

  async function promoteCanary() {
    setPromoteError(null);
    setPromoteMessage(null);
    const { data, error } = await api.POST("/v1/skills/{skill_id}/promote-canary", {
      params: { path: { skill_id: skillId } },
      body: { shadow_deployment_id: shadowDeploymentIdForPromotion, reason: "product-web-application" },
    });
    if (error) {
      setPromoteError("No se pudo promover a canary (revisa elegibilidad del shadow deployment).");
      return;
    }
    setPromoteMessage(`Promovido a canary: ${data.id} (${data.status})`);
  }

  async function promoteActive() {
    setPromoteError(null);
    setPromoteMessage(null);
    const { data, error } = await api.POST("/v1/skills/{skill_id}/promote-active", {
      params: { path: { skill_id: skillId } },
      body: { reason: "product-web-application" },
    });
    if (error) {
      setPromoteError("No se pudo promover a activo.");
      return;
    }
    setPromoteMessage(`Promovido a activo: ${data.id} (${data.status})`);
  }

  async function rollback() {
    setPromoteError(null);
    setPromoteMessage(null);
    const { data, error } = await api.POST("/v1/skills/rollback", {
      body: { process_key: processKeyForRollback, reason: "product-web-application" },
    });
    if (error) {
      setPromoteError("No se pudo revertir el despliegue.");
      return;
    }
    setPromoteMessage(data.active ? `Activo restaurado: ${data.active.id}` : "No hay paquete activo previo.");
  }

  async function createShadow() {
    setShadowError(null);
    setShadow(null);
    const { data, error } = await api.POST("/v1/deployments/shadow", {
      body: {
        candidate_id: candidateId,
        proof_id: proofId,
        object_type: objectType,
        agreement_threshold: 0.9,
        minimum_case_count: 30,
        minimum_decision_coverage: 1.0,
        minimum_review_coverage: 0.5,
        minimum_outcome_reconciliation: 0.5,
        observation_window_hours: 168,
      },
    });
    if (error) {
      setShadowError("No se pudo crear el shadow deployment.");
      return;
    }
    setShadow({ id: data.id, status: data.status });
    setDeploymentId(data.id);
  }

  async function loadDashboard() {
    setDashboardError(null);
    setDashboard(null);
    const { data, error } = await api.GET("/v1/deployments/{deployment_id}/dashboard", {
      params: { path: { deployment_id: deploymentId } },
    });
    if (error) {
      setDashboardError("No se encontró el shadow deployment.");
      return;
    }
    setDashboard(data);
  }

  return (
    <div>
      <h2>Despliegues</h2>

      <div className="card">
        <h3>Compilar candidato a skill package</h3>
        <label>
          Candidate ID
          <br />
          <input value={compileCandidateId} onChange={(event) => setCompileCandidateId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Connector ID
          <br />
          <input value={connectorId} onChange={(event) => setConnectorId(event.target.value)} />
        </label>
        <br />
        <label>
          Pasos del flujo (JSON)
          <br />
          <textarea value={workflowStepsJson} onChange={(event) => setWorkflowStepsJson(event.target.value)} rows={3} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={compile}>
            Compilar
          </button>
        </p>
        {compileError && <ErrorState message={compileError} />}
        {skillPackage && (
          <p>
            Skill package <strong>{skillPackage.id}</strong> -- <StatusBadge status={skillPackage.status} />
          </p>
        )}
      </div>

      <div className="card">
        <h3>Paquete de skill</h3>
        <label>
          Skill ID
          <br />
          <input value={skillId} onChange={(event) => setSkillId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Version ID
          <br />
          <input value={versionId} onChange={(event) => setVersionId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={loadSkillPackage}>
            Consultar
          </button>{" "}
          <button className="primary" onClick={approveSkillPackage}>
            Aprobar
          </button>
        </p>
        {skillError && <ErrorState message={skillError} />}
        {skillDetail !== null && <JsonBlock value={skillDetail} />}
      </div>

      <div className="card">
        <h3>Promoción y reversión</h3>
        <label>
          Shadow deployment ID (para promover a canary)
          <br />
          <input
            value={shadowDeploymentIdForPromotion}
            onChange={(event) => setShadowDeploymentIdForPromotion(event.target.value)}
            style={{ width: "100%" }}
          />
        </label>
        <p>
          <button className="primary" onClick={promoteCanary}>
            Promover a canary
          </button>{" "}
          <button className="primary" onClick={promoteActive}>
            Promover a activo
          </button>
        </p>
        <label>
          Process key (para revertir)
          <br />
          <input value={processKeyForRollback} onChange={(event) => setProcessKeyForRollback(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={rollback}>
            Revertir
          </button>
        </p>
        {promoteError && <ErrorState message={promoteError} />}
        {promoteMessage && <p className="badge badge-ok">{promoteMessage}</p>}
      </div>

      <div className="card">
        <h3>Shadow deployment</h3>
        <label>
          Candidate ID
          <br />
          <input value={candidateId} onChange={(event) => setCandidateId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Proof ID
          <br />
          <input value={proofId} onChange={(event) => setProofId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Object type
          <br />
          <input value={objectType} onChange={(event) => setObjectType(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={createShadow}>
            Crear shadow deployment
          </button>
        </p>
        {shadowError && <ErrorState message={shadowError} />}
        {shadow && (
          <p>
            Deployment <strong>{shadow.id}</strong> -- <StatusBadge status={shadow.status} />
          </p>
        )}

        <label>
          Deployment ID (dashboard)
          <br />
          <input value={deploymentId} onChange={(event) => setDeploymentId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={loadDashboard}>
            Ver dashboard
          </button>
        </p>
        {dashboardError && <ErrorState message={dashboardError} />}
        {dashboard !== null && <JsonBlock value={dashboard} />}
      </div>
    </div>
  );
}
