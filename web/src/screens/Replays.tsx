import { useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import { JsonBlock } from "../components/JsonBlock";
import { StatusBadge } from "../components/StatusBadge";

export function Replays() {
  // Create replay
  const [processKey, setProcessKey] = useState("");
  const [version, setVersion] = useState("");
  const [objectType, setObjectType] = useState("sales_order");
  const [createError, setCreateError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ id: string; status: string } | null>(null);

  // Get replay
  const [replayId, setReplayId] = useState("");
  const [replay, setReplay] = useState<unknown>(null);
  const [replayError, setReplayError] = useState<string | null>(null);
  const [cases, setCases] = useState<unknown>(null);

  // Comparison
  const [baselineReplayId, setBaselineReplayId] = useState("");
  const [comparison, setComparison] = useState<unknown>(null);
  const [comparisonError, setComparisonError] = useState<string | null>(null);

  // Proof
  const [proofBenchmarkVersion, setProofBenchmarkVersion] = useState("v1");
  const [proof, setProof] = useState<unknown>(null);
  const [proofError, setProofError] = useState<string | null>(null);
  const [proofId, setProofId] = useState("");

  async function createReplay() {
    setCreateError(null);
    setCreated(null);
    const { data, error } = await api.POST("/v1/processes/{process_key}/versions/{version}/replays", {
      params: { path: { process_key: processKey, version } },
      body: { object_type: objectType },
    });
    if (error) {
      setCreateError("No se pudo crear el replay (revisa que el proceso exista).");
      return;
    }
    setCreated({ id: data.id, status: data.status });
    setReplayId(data.id);
  }

  async function loadReplay() {
    setReplayError(null);
    setReplay(null);
    setCases(null);
    const [replayResult, casesResult] = await Promise.all([
      api.GET("/v1/replays/{replay_id}", { params: { path: { replay_id: replayId } } }),
      api.GET("/v1/replays/{replay_id}/cases", { params: { path: { replay_id: replayId } } }),
    ]);
    if (replayResult.error) {
      setReplayError("No se encontró el replay.");
      return;
    }
    setReplay(replayResult.data);
    if (!casesResult.error) setCases(casesResult.data);
  }

  async function freezeReplay() {
    setReplayError(null);
    const { data, error } = await api.POST("/v1/replays/{replay_id}/freeze", {
      params: { path: { replay_id: replayId } },
    });
    if (error) {
      setReplayError("No se pudo congelar el replay.");
      return;
    }
    setReplay(data);
  }

  async function loadComparison() {
    setComparisonError(null);
    setComparison(null);
    const { data, error } = await api.GET("/v1/replays/{replay_id}/comparison", {
      params: { path: { replay_id: replayId }, query: { baseline_replay_id: baselineReplayId } },
    });
    if (error) {
      setComparisonError("No se pudo comparar los replays.");
      return;
    }
    setComparison(data);
  }

  async function generateProof() {
    setProofError(null);
    setProof(null);
    const { data, error } = await api.POST("/v1/replays/{replay_id}/proofs", {
      params: { path: { replay_id: replayId } },
      body: { baseline_replay_id: baselineReplayId, benchmark_version: proofBenchmarkVersion },
    });
    if (error) {
      setProofError("No se pudo generar la prueba de mejora.");
      return;
    }
    setProof(data);
  }

  async function loadProof() {
    setProofError(null);
    setProof(null);
    const { data, error } = await api.GET("/v1/proofs/{proof_id}", { params: { path: { proof_id: proofId } } });
    if (error) {
      setProofError("No se encontró la prueba.");
      return;
    }
    setProof(data);
  }

  return (
    <div>
      <h2>Replays</h2>

      <div className="card">
        <h3>Crear replay</h3>
        <label>
          Process key
          <br />
          <input value={processKey} onChange={(event) => setProcessKey(event.target.value)} />
        </label>{" "}
        <label>
          Versión
          <br />
          <input value={version} onChange={(event) => setVersion(event.target.value)} />
        </label>{" "}
        <label>
          Object type
          <br />
          <input value={objectType} onChange={(event) => setObjectType(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={createReplay}>
            Crear
          </button>
        </p>
        {createError && <ErrorState message={createError} />}
        {created && (
          <p>
            Replay <strong>{created.id}</strong> -- <StatusBadge status={created.status} />
          </p>
        )}
      </div>

      <div className="card">
        <h3>Consultar replay</h3>
        <label>
          Replay ID
          <br />
          <input value={replayId} onChange={(event) => setReplayId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={loadReplay}>
            Consultar
          </button>{" "}
          <button className="primary" onClick={freezeReplay}>
            Congelar
          </button>
        </p>
        {replayError && <ErrorState message={replayError} />}
        {replay !== null && <JsonBlock value={replay} />}
        {cases !== null && (
          <>
            <h4>Casos</h4>
            <JsonBlock value={cases} />
          </>
        )}
      </div>

      <div className="card">
        <h3>Comparación y prueba de mejora</h3>
        <label>
          Replay base (baseline)
          <br />
          <input
            value={baselineReplayId}
            onChange={(event) => setBaselineReplayId(event.target.value)}
            style={{ width: "100%" }}
          />
        </label>
        <p>
          <button className="primary" onClick={loadComparison}>
            Comparar con el replay consultado
          </button>
        </p>
        {comparisonError && <ErrorState message={comparisonError} />}
        {comparison !== null && <JsonBlock value={comparison} />}

        <label>
          Versión de benchmark
          <br />
          <input value={proofBenchmarkVersion} onChange={(event) => setProofBenchmarkVersion(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={generateProof}>
            Generar prueba de mejora
          </button>
        </p>
        <label>
          Proof ID
          <br />
          <input value={proofId} onChange={(event) => setProofId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={loadProof}>
            Consultar prueba
          </button>
        </p>
        {proofError && <ErrorState message={proofError} />}
        {proof !== null && <JsonBlock value={proof} />}
      </div>
    </div>
  );
}
