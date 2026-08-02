import { useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import { StatusBadge } from "../components/StatusBadge";
import { DataTable } from "../components/DataTable";
import { JsonBlock } from "../components/JsonBlock";

interface RoutingDecision {
  id: string;
  business_object_key: string | null;
  selected_lane: string;
  selection_reason: string;
  created_at: string;
}

interface Incident {
  id: string;
  incident_type: string;
  severity: string;
  created_at: string;
  resolved_at: string | null;
}

interface Dashboard {
  status?: string;
  stable_case_count?: number;
  canary_case_count?: number;
  success_count?: number;
  blocked_count?: number;
  failed_count?: number;
  cumulative_amount?: number;
  unexpected_side_effect_count?: number;
  estimated_opportunity_value?: string | null;
  recommend?: string;
  [key: string]: unknown;
}

export function Canary() {
  // Create
  const [processKey, setProcessKey] = useState("");
  const [stableSkillPackageId, setStableSkillPackageId] = useState("");
  const [canarySkillPackageId, setCanarySkillPackageId] = useState("");
  const [shadowDeploymentId, setShadowDeploymentId] = useState("");
  const [percentageBasisPoints, setPercentageBasisPoints] = useState("1000");
  const [maximumCases, setMaximumCases] = useState("50");
  const [maximumTotalAmount, setMaximumTotalAmount] = useState("10000");
  const [maximumAmount, setMaximumAmount] = useState("5000");
  const [createError, setCreateError] = useState<string | null>(null);
  const [policy, setPolicy] = useState<{ id: string; status: string } | null>(null);

  // Lifecycle / dashboard
  const [policyId, setPolicyId] = useState("");
  const [approvalId, setApprovalId] = useState("");
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [routingDecisions, setRoutingDecisions] = useState<RoutingDecision[] | null>(null);
  const [incidents, setIncidents] = useState<Incident[] | null>(null);

  // Incident resolve
  const [incidentIdToResolve, setIncidentIdToResolve] = useState("");
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [incidentError, setIncidentError] = useState<string | null>(null);

  async function createPolicy() {
    setCreateError(null);
    const { data, error } = await api.POST("/v1/canary-policies", {
      body: {
        process_key: processKey,
        stable_skill_package_id: stableSkillPackageId,
        canary_skill_package_id: canarySkillPackageId,
        shadow_deployment_id: shadowDeploymentId,
        percentage_basis_points: Number(percentageBasisPoints),
        maximum_cases: Number(maximumCases),
        maximum_total_amount: Number(maximumTotalAmount),
        maximum_amount: Number(maximumAmount),
        minimum_amount: 0,
      },
    });
    if (error) {
      setCreateError("No se pudo crear la política de canary.");
      return;
    }
    setPolicy({ id: data.id, status: data.status });
    setPolicyId(data.id);
  }

  async function approvePolicy() {
    setPolicyError(null);
    if (!policyId) return;
    const { data, error } = await api.POST("/v1/canary-policies/{policy_id}/approve", {
      params: { path: { policy_id: policyId } },
      body: { approval_id: approvalId },
    });
    if (error) {
      setPolicyError('No se pudo ejecutar la transición "approve".');
      return;
    }
    setPolicy({ id: data.id, status: data.status });
  }

  async function activatePolicy() {
    await runTransition("/v1/canary-policies/{policy_id}/activate", "activate");
  }
  async function pausePolicy() {
    await runTransition("/v1/canary-policies/{policy_id}/pause", "pause");
  }
  async function resumePolicy() {
    await runTransition("/v1/canary-policies/{policy_id}/resume", "resume");
  }
  async function abortPolicy() {
    await runTransition("/v1/canary-policies/{policy_id}/abort", "abort");
  }
  async function completePolicy() {
    await runTransition("/v1/canary-policies/{policy_id}/complete", "complete");
  }

  async function runTransition(
    path:
      | "/v1/canary-policies/{policy_id}/activate"
      | "/v1/canary-policies/{policy_id}/pause"
      | "/v1/canary-policies/{policy_id}/resume"
      | "/v1/canary-policies/{policy_id}/abort"
      | "/v1/canary-policies/{policy_id}/complete",
    label: string,
  ) {
    setPolicyError(null);
    if (!policyId) return;
    const { data, error } = await api.POST(path, { params: { path: { policy_id: policyId } } });
    if (error) {
      setPolicyError(`No se pudo ejecutar la transición "${label}".`);
      return;
    }
    setPolicy({ id: data.id, status: data.status });
  }

  async function loadDashboard() {
    setPolicyError(null);
    const { data, error } = await api.GET("/v1/canary-policies/{policy_id}/dashboard", {
      params: { path: { policy_id: policyId } },
    });
    if (error) {
      setPolicyError("No se encontró la política de canary.");
      return;
    }
    setDashboard(data as Dashboard);
  }

  async function loadRoutingDecisions() {
    const { data, error } = await api.GET("/v1/canary-policies/{policy_id}/routing-decisions", {
      params: { path: { policy_id: policyId } },
    });
    if (!error) setRoutingDecisions(data as RoutingDecision[]);
  }

  async function loadIncidents() {
    const { data, error } = await api.GET("/v1/canary-policies/{policy_id}/incidents", {
      params: { path: { policy_id: policyId } },
    });
    if (!error) setIncidents(data as Incident[]);
  }

  async function resolveIncident() {
    setIncidentError(null);
    const { data, error } = await api.POST("/v1/canary-policies/incidents/{incident_id}/resolve", {
      params: { path: { incident_id: incidentIdToResolve } },
      body: { resolution_notes: resolutionNotes },
    });
    if (error) {
      setIncidentError("No se pudo resolver el incidente.");
      return;
    }
    setIncidents((prev) => (prev ? prev.map((incident) => (incident.id === data.id ? data : incident)) : [data]));
  }

  return (
    <div>
      <h2>Canary</h2>

      <div className="card">
        <h3>Crear política</h3>
        <label>
          Process key
          <br />
          <input value={processKey} onChange={(event) => setProcessKey(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Stable skill package ID
          <br />
          <input value={stableSkillPackageId} onChange={(event) => setStableSkillPackageId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Canary skill package ID
          <br />
          <input value={canarySkillPackageId} onChange={(event) => setCanarySkillPackageId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Shadow deployment ID
          <br />
          <input value={shadowDeploymentId} onChange={(event) => setShadowDeploymentId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          % en basis points
          <input value={percentageBasisPoints} onChange={(event) => setPercentageBasisPoints(event.target.value)} />
        </label>{" "}
        <label>
          Máx. casos
          <input value={maximumCases} onChange={(event) => setMaximumCases(event.target.value)} />
        </label>{" "}
        <label>
          Máx. importe total
          <input value={maximumTotalAmount} onChange={(event) => setMaximumTotalAmount(event.target.value)} />
        </label>{" "}
        <label>
          Máx. importe por caso
          <input value={maximumAmount} onChange={(event) => setMaximumAmount(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={createPolicy}>
            Crear
          </button>
        </p>
        {createError && <ErrorState message={createError} />}
        {policy && (
          <p>
            Policy <strong>{policy.id}</strong> -- <StatusBadge status={policy.status} />
          </p>
        )}
      </div>

      <div className="card">
        <h3>Ciclo de vida y dashboard</h3>
        <label>
          Policy ID
          <br />
          <input value={policyId} onChange={(event) => setPolicyId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Approval ID (para aprobar)
          <br />
          <input value={approvalId} onChange={(event) => setApprovalId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={approvePolicy}>
            Aprobar
          </button>{" "}
          <button className="primary" onClick={activatePolicy}>
            Activar
          </button>{" "}
          <button className="primary" onClick={pausePolicy}>
            Pausar
          </button>{" "}
          <button className="primary" onClick={resumePolicy}>
            Reanudar
          </button>{" "}
          <button className="primary" onClick={abortPolicy}>
            Abortar
          </button>{" "}
          <button className="primary" onClick={completePolicy}>
            Completar
          </button>
        </p>
        <p>
          <button className="primary" onClick={loadDashboard}>
            Ver dashboard
          </button>{" "}
          <button className="primary" onClick={loadRoutingDecisions}>
            Ver decisiones de enrutado
          </button>{" "}
          <button className="primary" onClick={loadIncidents}>
            Ver incidentes
          </button>
        </p>
        {policyError && <ErrorState message={policyError} />}

        {dashboard && (
          <div>
            {dashboard.recommend && (
              <div className="disclaimer" role="status">
                <strong>Recomendación asesora (no se ejecuta automáticamente):</strong> {dashboard.recommend}
              </div>
            )}
            <JsonBlock value={dashboard} />
          </div>
        )}

        {routingDecisions && (
          <>
            <h4>Decisiones de enrutado</h4>
            <DataTable
              rows={routingDecisions}
              rowKey={(row) => row.id}
              columns={[
                { key: "obj", header: "Objeto", render: (row) => row.business_object_key ?? "--" },
                { key: "lane", header: "Carril", render: (row) => row.selected_lane },
                { key: "reason", header: "Motivo", render: (row) => row.selection_reason },
                { key: "at", header: "Fecha", render: (row) => row.created_at },
              ]}
            />
          </>
        )}

        {incidents && (
          <>
            <h4>Incidentes</h4>
            <DataTable
              rows={incidents}
              rowKey={(row) => row.id}
              columns={[
                { key: "type", header: "Tipo", render: (row) => row.incident_type },
                { key: "sev", header: "Severidad", render: (row) => <StatusBadge status={row.severity} /> },
                { key: "resolved", header: "Resuelto", render: (row) => (row.resolved_at ? "sí" : "no") },
              ]}
            />
          </>
        )}
      </div>

      <div className="card">
        <h3>Resolver incidente</h3>
        <label>
          Incident ID
          <br />
          <input value={incidentIdToResolve} onChange={(event) => setIncidentIdToResolve(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Notas de resolución
          <br />
          <input value={resolutionNotes} onChange={(event) => setResolutionNotes(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={resolveIncident}>
            Resolver
          </button>
        </p>
        {incidentError && <ErrorState message={incidentError} />}
      </div>
    </div>
  );
}
