import { useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import { JsonBlock } from "../components/JsonBlock";
import { StatusBadge } from "../components/StatusBadge";
import { DataTable } from "../components/DataTable";

interface ManifestEntry {
  resource_type: string;
  resource_id: string;
  reality_label: string;
  content_hash: string;
}

interface EvidenceBundle {
  id: string;
  status: string;
  manifest: ManifestEntry[];
  missing_resources: string[];
  manifest_hash: string;
  content_hash: string;
  chain_hash: string;
}

interface VerifyResult {
  verified: boolean;
  stored_hashes_intact: boolean;
  live_mismatches: string[];
}

export function Evidence() {
  // Execution evidence
  const [runId, setRunId] = useState("");
  const [runEvidence, setRunEvidence] = useState<unknown>(null);
  const [runEvidenceError, setRunEvidenceError] = useState<string | null>(null);

  // Decision evidence bundle
  const [recommendationId, setRecommendationId] = useState("");
  const [measurementPlanId, setMeasurementPlanId] = useState("");
  const [bundle, setBundle] = useState<EvidenceBundle | null>(null);
  const [bundleId, setBundleId] = useState("");
  const [bundleError, setBundleError] = useState<string | null>(null);
  const [verifyResult, setVerifyResult] = useState<VerifyResult | null>(null);

  async function loadRunEvidence() {
    setRunEvidenceError(null);
    setRunEvidence(null);
    const { data, error } = await api.GET("/v1/runs/{run_id}/evidence", { params: { path: { run_id: runId } } });
    if (error) {
      setRunEvidenceError("La evidencia de ejecución no está disponible para ese run.");
      return;
    }
    setRunEvidence(data);
  }

  async function createBundle() {
    setBundleError(null);
    const { data, error } = await api.POST("/v1/recommendations/{recommendation_id}/evidence-bundle", {
      params: { path: { recommendation_id: recommendationId } },
      body: { measurement_plan_id: measurementPlanId || null },
    });
    if (error) {
      setBundleError("No se pudo construir el bundle de evidencia.");
      return;
    }
    setBundle(data as unknown as EvidenceBundle);
    setBundleId(data.id);
  }

  async function loadBundle() {
    setBundleError(null);
    const { data, error } = await api.GET("/v1/decision-outcome-evidence/{bundle_id}", {
      params: { path: { bundle_id: bundleId } },
    });
    if (error) {
      setBundleError("No se encontró el bundle de evidencia, o falló la revalidación de hashes almacenados.");
      return;
    }
    setBundle(data as unknown as EvidenceBundle);
  }

  async function verifyBundle() {
    setBundleError(null);
    setVerifyResult(null);
    const { data, error } = await api.GET("/v1/decision-outcome-evidence/{bundle_id}/verify", {
      params: { path: { bundle_id: bundleId } },
    });
    if (error) {
      setBundleError("No se pudo verificar el bundle.");
      return;
    }
    setVerifyResult(data);
  }

  function exportBundle() {
    if (!bundle) return;
    const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `decision-outcome-evidence-${bundle.id}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <h2>Evidencia</h2>

      <div className="card">
        <h3>Evidencia de ejecución</h3>
        <label>
          Run ID
          <br />
          <input value={runId} onChange={(event) => setRunId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={loadRunEvidence}>
            Consultar evidencia
          </button>
        </p>
        {runEvidenceError && <ErrorState message={runEvidenceError} />}
        {runEvidence !== null && <JsonBlock value={runEvidence} />}
      </div>

      <div className="card">
        <h3>Bundle de evidencia decisión-a-resultado</h3>
        <label>
          Recommendation ID (para construir)
          <br />
          <input value={recommendationId} onChange={(event) => setRecommendationId(event.target.value)} style={{ width: "100%" }} />
        </label>{" "}
        <label>
          Measurement plan ID (opcional)
          <br />
          <input value={measurementPlanId} onChange={(event) => setMeasurementPlanId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={createBundle}>
            Construir / sellar bundle
          </button>
        </p>

        <label>
          Bundle ID
          <br />
          <input value={bundleId} onChange={(event) => setBundleId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={loadBundle}>
            Consultar
          </button>{" "}
          <button className="primary" onClick={verifyBundle}>
            Verificar
          </button>{" "}
          <button className="primary" onClick={exportBundle} disabled={!bundle}>
            Exportar JSON
          </button>
        </p>
        {bundleError && <ErrorState message={bundleError} />}

        {bundle && (
          <div>
            <p>
              Estado de la cadena: <StatusBadge status={bundle.status} />
            </p>
            {bundle.missing_resources.length > 0 && (
              <ErrorState message={`Recursos faltantes: ${bundle.missing_resources.join(", ")}`} />
            )}
            <DataTable
              rows={bundle.manifest}
              rowKey={(row) => `${row.resource_type}:${row.resource_id}`}
              columns={[
                { key: "type", header: "Tipo de recurso", render: (row) => row.resource_type },
                { key: "id", header: "ID", render: (row) => row.resource_id },
                { key: "label", header: "Etiqueta de realidad", render: (row) => <StatusBadge status={row.reality_label} /> },
                { key: "hash", header: "Content hash", render: (row) => <code>{row.content_hash.slice(0, 16)}...</code> },
              ]}
            />
            <p>
              manifest_hash: <code>{bundle.manifest_hash}</code>
              <br />
              chain_hash: <code>{bundle.chain_hash}</code>
            </p>
          </div>
        )}

        {verifyResult && (
          <div>
            <p>
              stored_hashes_intact: <StatusBadge status={String(verifyResult.stored_hashes_intact)} /> -- verified:{" "}
              <StatusBadge status={String(verifyResult.verified)} />
            </p>
            {verifyResult.live_mismatches.length > 0 && (
              <ErrorState message={`Discrepancias en vivo: ${verifyResult.live_mismatches.join(", ")}`} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
