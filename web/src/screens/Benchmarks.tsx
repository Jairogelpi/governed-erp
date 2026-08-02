import { useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import { StatusBadge } from "../components/StatusBadge";
import { JsonBlock } from "../components/JsonBlock";

const CONFIGURATION_OPTIONS = ["fixed_workflow", "direct_tool_agent", "erpguard_candidate"];

interface BenchmarkReport {
  dataset_version: string;
  disclaimer: string;
  configurations: Record<string, Record<string, unknown>>;
  comparison: Record<string, unknown>;
}

export function Benchmarks() {
  const [datasetVersion, setDatasetVersion] = useState("quote_to_order_v1_seed92");
  const [selectedConfigurations, setSelectedConfigurations] = useState<string[]>([...CONFIGURATION_OPTIONS]);
  const [repeats, setRepeats] = useState("1");
  const [createError, setCreateError] = useState<string | null>(null);
  const [run, setRun] = useState<{ id: string; status: string } | null>(null);

  const [runId, setRunId] = useState("");
  const [runDetail, setRunDetail] = useState<{ status: string } | null>(null);
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  function toggleConfiguration(name: string) {
    setSelectedConfigurations((prev) =>
      prev.includes(name) ? prev.filter((item) => item !== name) : [...prev, name],
    );
  }

  async function createRun() {
    setCreateError(null);
    const { data, error } = await api.POST("/v1/benchmarks/runs", {
      body: { dataset_version: datasetVersion, configurations: selectedConfigurations, repeats: Number(repeats) },
    });
    if (error) {
      setCreateError("No se pudo crear la ejecución de benchmark.");
      return;
    }
    setRun({ id: data.id, status: data.status });
    setRunId(data.id);
  }

  async function loadRun() {
    setReportError(null);
    const { data, error } = await api.GET("/v1/benchmarks/runs/{run_id}", { params: { path: { run_id: runId } } });
    if (error) {
      setReportError("No se encontró la ejecución de benchmark.");
      return;
    }
    setRunDetail(data);
  }

  async function loadReport() {
    setReportError(null);
    setReport(null);
    const { data, error } = await api.GET("/v1/benchmarks/runs/{run_id}/report", { params: { path: { run_id: runId } } });
    if (error) {
      setReportError("No se pudo generar el informe (¿la ejecución ya se completó?).");
      return;
    }
    setReport(data as BenchmarkReport);
  }

  const allMetricNames = report
    ? Array.from(
        new Set(Object.values(report.configurations).flatMap((metrics) => Object.keys(metrics))),
      )
    : [];

  function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
  }

  const scalarMetricNames = report
    ? allMetricNames.filter(
        (metric) => !Object.values(report.configurations).some((cfg) => isPlainObject(cfg[metric])),
      )
    : [];

  const structuredMetricNames = report
    ? allMetricNames.filter((metric) => !scalarMetricNames.includes(metric))
    : [];

  return (
    <div>
      <h2>Benchmarks (ERPRiskBench)</h2>

      <div className="card">
        <h3>Lanzar ejecución</h3>
        <label>
          Dataset version
          <br />
          <input value={datasetVersion} onChange={(event) => setDatasetVersion(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        {CONFIGURATION_OPTIONS.map((name) => (
          <label key={name} style={{ marginRight: "1rem" }}>
            <input
              type="checkbox"
              checked={selectedConfigurations.includes(name)}
              onChange={() => toggleConfiguration(name)}
            />{" "}
            {name}
          </label>
        ))}
        <br />
        <label>
          Repeticiones
          <br />
          <input value={repeats} onChange={(event) => setRepeats(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={createRun}>
            Lanzar
          </button>
        </p>
        {createError && <ErrorState message={createError} />}
        {run && (
          <p>
            Run <strong>{run.id}</strong> -- <StatusBadge status={run.status} />
          </p>
        )}
      </div>

      <div className="card">
        <h3>Consultar informe</h3>
        <label>
          Run ID
          <br />
          <input value={runId} onChange={(event) => setRunId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={loadRun}>
            Consultar estado
          </button>{" "}
          <button className="primary" onClick={loadReport}>
            Ver informe comparativo
          </button>
        </p>
        {runDetail && (
          <p>
            Estado: <StatusBadge status={runDetail.status} />
          </p>
        )}
        {reportError && <ErrorState message={reportError} />}
        {report && (
          <div>
            <p className="disclaimer">{report.disclaimer}</p>
            <table>
              <thead>
                <tr>
                  <th>Métrica</th>
                  {Object.keys(report.configurations).map((name) => (
                    <th key={name}>{name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {scalarMetricNames.map((metric) => (
                  <tr key={metric}>
                    <td>{metric}</td>
                    {Object.keys(report.configurations).map((name) => (
                      <td key={name}>{String(report.configurations[name][metric] ?? "--")}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {structuredMetricNames.map((metric) => (
              <div key={metric}>
                <h4>{metric}</h4>
                <JsonBlock
                  value={Object.fromEntries(
                    Object.keys(report.configurations).map((name) => [
                      name,
                      report.configurations[name][metric],
                    ]),
                  )}
                />
              </div>
            ))}
            <h4>Comparación</h4>
            <JsonBlock value={report.comparison} />
          </div>
        )}
      </div>
    </div>
  );
}
