import { useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import { JsonBlock } from "../components/JsonBlock";
import { DataTable } from "../components/DataTable";

interface VariantSummary {
  variant_id: string;
  sequence: string[];
  case_count: number;
  duration_seconds: number | null;
  case_ids: string[];
}

export function Processes() {
  // Process lookup
  const [processKey, setProcessKey] = useState("");
  const [version, setVersion] = useState("");
  const [processDefinition, setProcessDefinition] = useState<unknown>(null);
  const [processError, setProcessError] = useState<string | null>(null);

  // Diff
  const [fromVersion, setFromVersion] = useState("");
  const [toVersion, setToVersion] = useState("");
  const [diff, setDiff] = useState<unknown>(null);
  const [diffError, setDiffError] = useState<string | null>(null);

  // Register
  const [yaml, setYaml] = useState("");
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [registerOk, setRegisterOk] = useState<string | null>(null);

  // Variants
  const [objectType, setObjectType] = useState("sales_order");
  const [variants, setVariants] = useState<VariantSummary[] | null>(null);
  const [variantsError, setVariantsError] = useState<string | null>(null);
  const [caseId, setCaseId] = useState("");
  const [caseTrace, setCaseTrace] = useState<unknown>(null);
  const [caseError, setCaseError] = useState<string | null>(null);

  // Candidate builder
  const [candidateProcessKey, setCandidateProcessKey] = useState("");
  const [baseVersion, setBaseVersion] = useState("");
  const [candidateVersion, setCandidateVersion] = useState("");
  const [changesJson, setChangesJson] = useState("{}");
  const [evidenceRefs, setEvidenceRefs] = useState("");
  const [candidate, setCandidate] = useState<{ id: string; status: string } | null>(null);
  const [candidateError, setCandidateError] = useState<string | null>(null);

  async function loadProcess() {
    setProcessError(null);
    setProcessDefinition(null);
    const { data, error } = await api.GET("/v1/processes/{process_key}/versions/{version}", {
      params: { path: { process_key: processKey, version } },
    });
    if (error) {
      setProcessError("No se encontró esa versión del proceso.");
      return;
    }
    setProcessDefinition(data);
  }

  async function loadDiff() {
    setDiffError(null);
    setDiff(null);
    const { data, error } = await api.GET("/v1/processes/{process_key}/diff", {
      params: { path: { process_key: processKey }, query: { from_version: fromVersion, to_version: toVersion } },
    });
    if (error) {
      setDiffError("No se pudo calcular el diff.");
      return;
    }
    setDiff(data);
  }

  async function registerProcess() {
    setRegisterError(null);
    setRegisterOk(null);
    const { data, error } = await api.POST("/v1/processes", { body: { yaml } });
    if (error) {
      setRegisterError("YAML inválido o conflicto de versión.");
      return;
    }
    setRegisterOk(`Registrado: ${data.process_key} v${data.version}`);
  }

  async function loadVariants() {
    setVariantsError(null);
    setVariants(null);
    const { data, error } = await api.GET("/v1/variants", { params: { query: { object_type: objectType } } });
    if (error) {
      setVariantsError("No se pudieron cargar las variantes.");
      return;
    }
    setVariants(data as VariantSummary[]);
  }

  async function loadCaseTrace() {
    setCaseError(null);
    setCaseTrace(null);
    const { data, error } = await api.GET("/v1/variants/cases/{case_id}", {
      params: { path: { case_id: caseId }, query: { object_type: objectType } },
    });
    if (error) {
      setCaseError("No se encontró el caso.");
      return;
    }
    setCaseTrace(data);
  }

  async function createCandidate() {
    setCandidateError(null);
    setCandidate(null);
    let changes: Record<string, unknown>;
    try {
      changes = JSON.parse(changesJson);
    } catch {
      setCandidateError("El JSON de cambios no es válido.");
      return;
    }
    const { data, error } = await api.POST("/v1/process-candidates", {
      body: {
        process_key: candidateProcessKey,
        base_version: baseVersion,
        candidate_version: candidateVersion,
        changes,
        evidence_refs: evidenceRefs.split(",").map((item) => item.trim()).filter(Boolean),
      },
    });
    if (error) {
      setCandidateError("No se pudo crear el candidato (revisa evidencia y versión base).");
      return;
    }
    setCandidate({ id: data.id, status: data.status });
  }

  async function submitCandidate() {
    if (!candidate) return;
    const { data, error } = await api.POST("/v1/process-candidates/{candidate_id}/submit", {
      params: { path: { candidate_id: candidate.id } },
    });
    if (error) {
      setCandidateError("No se pudo enviar el candidato.");
      return;
    }
    setCandidate({ id: data.id, status: data.status });
  }

  return (
    <div>
      <h2>Procesos</h2>

      <div className="card">
        <h3>Consultar versión de proceso</h3>
        <label>
          Process key
          <br />
          <input value={processKey} onChange={(event) => setProcessKey(event.target.value)} />
        </label>{" "}
        <label>
          Versión
          <br />
          <input value={version} onChange={(event) => setVersion(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={loadProcess}>
            Consultar
          </button>
        </p>
        {processError && <ErrorState message={processError} />}
        {processDefinition !== null && <JsonBlock value={processDefinition} />}
      </div>

      <div className="card">
        <h3>Diferencia entre versiones</h3>
        <label>
          Desde
          <br />
          <input value={fromVersion} onChange={(event) => setFromVersion(event.target.value)} />
        </label>{" "}
        <label>
          Hasta
          <br />
          <input value={toVersion} onChange={(event) => setToVersion(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={loadDiff}>
            Comparar
          </button>
        </p>
        {diffError && <ErrorState message={diffError} />}
        {diff !== null && <JsonBlock value={diff} />}
      </div>

      <div className="card">
        <h3>Registrar proceso (YAML)</h3>
        <textarea value={yaml} onChange={(event) => setYaml(event.target.value)} rows={6} style={{ width: "100%" }} />
        <p>
          <button className="primary" onClick={registerProcess}>
            Registrar
          </button>
        </p>
        {registerError && <ErrorState message={registerError} />}
        {registerOk && <p className="badge badge-ok">{registerOk}</p>}
      </div>

      <div className="card">
        <h3>Explorador de variantes</h3>
        <label>
          Object type
          <br />
          <input value={objectType} onChange={(event) => setObjectType(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={loadVariants}>
            Descubrir variantes
          </button>
        </p>
        {variantsError && <ErrorState message={variantsError} />}
        {variants && (
          <DataTable
            rows={variants}
            rowKey={(row) => row.variant_id}
            columns={[
              { key: "id", header: "Variante", render: (row) => row.variant_id },
              { key: "cases", header: "Casos", render: (row) => row.case_count },
              { key: "duration", header: "Duración (s)", render: (row) => row.duration_seconds ?? "--" },
              { key: "seq", header: "Secuencia", render: (row) => row.sequence.join(" → ") },
            ]}
          />
        )}
        <label>
          Case ID para trazar
          <br />
          <input value={caseId} onChange={(event) => setCaseId(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={loadCaseTrace}>
            Ver traza del caso
          </button>
        </p>
        {caseError && <ErrorState message={caseError} />}
        {caseTrace !== null && <JsonBlock value={caseTrace} />}
      </div>

      <div className="card">
        <h3>Constructor de candidatos</h3>
        <label>
          Process key
          <br />
          <input value={candidateProcessKey} onChange={(event) => setCandidateProcessKey(event.target.value)} />
        </label>{" "}
        <label>
          Versión base
          <br />
          <input value={baseVersion} onChange={(event) => setBaseVersion(event.target.value)} />
        </label>{" "}
        <label>
          Versión candidata
          <br />
          <input value={candidateVersion} onChange={(event) => setCandidateVersion(event.target.value)} />
        </label>
        <br />
        <label>
          Cambios (JSON)
          <br />
          <textarea
            value={changesJson}
            onChange={(event) => setChangesJson(event.target.value)}
            rows={4}
            style={{ width: "100%" }}
          />
        </label>
        <br />
        <label>
          Referencias de evidencia (separadas por coma)
          <br />
          <input value={evidenceRefs} onChange={(event) => setEvidenceRefs(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={createCandidate}>
            Crear candidato
          </button>{" "}
          {candidate && candidate.status === "draft" && (
            <button className="primary" onClick={submitCandidate}>
              Enviar candidato
            </button>
          )}
        </p>
        {candidateError && <ErrorState message={candidateError} />}
        {candidate && (
          <p>
            Candidato <strong>{candidate.id}</strong> -- estado: {candidate.status}
          </p>
        )}
      </div>
    </div>
  );
}
