import { useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import { StatusBadge } from "../components/StatusBadge";
import { Disclaimer } from "../components/Disclaimer";

interface MeasurementPlan {
  id: string;
  status: string;
}

interface RealizedOutcomeReport {
  id: string;
  estimated_conservative: string;
  estimated_base: string;
  estimated_optimistic: string;
  observed_revenue_change: string | null;
  observed_margin_change: string | null;
  realized_value: string | null;
  implementation_cost: string | null;
  net_realized_value: string | null;
  result_classification: string;
  limitations: string[];
}

export function Outcomes() {
  // Create plan
  const [recommendationId, setRecommendationId] = useState("");
  const [comparisonMethod, setComparisonMethod] = useState("before_after_same_scope");
  const [observationStart, setObservationStart] = useState("");
  const [observationEnd, setObservationEnd] = useState("");
  const [implementationCost, setImplementationCost] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [plan, setPlan] = useState<MeasurementPlan | null>(null);

  // Lifecycle
  const [planId, setPlanId] = useState("");
  const [approvalId, setApprovalId] = useState("");
  const [planError, setPlanError] = useState<string | null>(null);

  // Capture followup
  const [netRevenue, setNetRevenue] = useState("");
  const [grossMargin, setGrossMargin] = useState("");
  const [grossMarginPercent, setGrossMarginPercent] = useState("");
  const [metricDefinitionVersion, setMetricDefinitionVersion] = useState("v1");
  const [captureError, setCaptureError] = useState<string | null>(null);

  // Report
  const [report, setReport] = useState<RealizedOutcomeReport | null>(null);
  const [reportId, setReportId] = useState("");
  const [reportError, setReportError] = useState<string | null>(null);

  async function createPlan() {
    setCreateError(null);
    const { data, error } = await api.POST("/v1/recommendations/{recommendation_id}/measurement-plans", {
      params: { path: { recommendation_id: recommendationId } },
      body: {
        comparison_method: comparisonMethod as
          | "before_after_same_scope"
          | "before_after_with_reference_segment"
          | "fixture_replay",
        observation_start: observationStart,
        observation_end: observationEnd,
        minimum_data_coverage: 0.8,
        implementation_cost: implementationCost || null,
      },
    });
    if (error) {
      setCreateError("No se pudo crear el plan de medición.");
      return;
    }
    setPlan(data);
    setPlanId(data.id);
  }

  async function approvePlan() {
    setPlanError(null);
    const { data, error } = await api.POST("/v1/measurement-plans/{plan_id}/approve", {
      params: { path: { plan_id: planId } },
      body: { approval_id: approvalId },
    });
    if (error) {
      setPlanError("No se pudo aprobar el plan.");
      return;
    }
    setPlan(data);
  }

  async function startPlan() {
    setPlanError(null);
    const { data, error } = await api.POST("/v1/measurement-plans/{plan_id}/start", {
      params: { path: { plan_id: planId } },
    });
    if (error) {
      setPlanError("No se pudo iniciar el plan.");
      return;
    }
    setPlan(data);
  }

  async function captureFollowup() {
    setCaptureError(null);
    const { error } = await api.POST("/v1/measurement-plans/{plan_id}/capture-followup", {
      params: { path: { plan_id: planId } },
      body: {
        observed: {
          net_revenue: netRevenue || null,
          gross_margin: grossMargin || null,
          gross_margin_percent: grossMarginPercent || null,
          metric_definition_version: metricDefinitionVersion,
          cost_coverage_rate: 1.0,
        },
        source: "fixture",
      },
    });
    if (error) {
      setCaptureError("No se pudo capturar el seguimiento.");
      return;
    }
  }

  async function evaluatePlan() {
    setPlanError(null);
    const { data, error } = await api.POST("/v1/measurement-plans/{plan_id}/evaluate", {
      params: { path: { plan_id: planId } },
    });
    if (error) {
      setPlanError("No se pudo evaluar el plan (revisa que tenga seguimiento capturado).");
      return;
    }
    setReport(data);
    setReportId(data.id);
  }

  async function loadReport() {
    setReportError(null);
    const { data, error } = await api.GET("/v1/outcome-reports/{report_id}", { params: { path: { report_id: reportId } } });
    if (error) {
      setReportError("No se encontró el informe de resultado.");
      return;
    }
    setReport(data);
  }

  return (
    <div>
      <h2>Resultados</h2>

      <div className="card">
        <h3>1. Crear plan de medición</h3>
        <label>
          Recommendation ID
          <br />
          <input value={recommendationId} onChange={(event) => setRecommendationId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Método de comparación
          <br />
          <select value={comparisonMethod} onChange={(event) => setComparisonMethod(event.target.value)}>
            <option value="before_after_same_scope">before_after_same_scope</option>
            <option value="before_after_with_reference_segment">before_after_with_reference_segment</option>
            <option value="fixture_replay">fixture_replay</option>
          </select>
        </label>
        <br />
        <label>
          Inicio de observación (YYYY-MM-DD)
          <br />
          <input value={observationStart} onChange={(event) => setObservationStart(event.target.value)} />
        </label>{" "}
        <label>
          Fin de observación (YYYY-MM-DD)
          <br />
          <input value={observationEnd} onChange={(event) => setObservationEnd(event.target.value)} />
        </label>
        <br />
        <label>
          Coste de implementación (opcional, evidenciado antes de conocer el resultado)
          <br />
          <input value={implementationCost} onChange={(event) => setImplementationCost(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={createPlan}>
            Crear plan
          </button>
        </p>
        {createError && <ErrorState message={createError} />}
        {plan && (
          <p>
            Plan <strong>{plan.id}</strong> -- <StatusBadge status={plan.status} />
          </p>
        )}
      </div>

      <div className="card">
        <h3>2. Aprobar → iniciar → capturar seguimiento → evaluar</h3>
        <label>
          Plan ID
          <br />
          <input value={planId} onChange={(event) => setPlanId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Approval ID
          <br />
          <input value={approvalId} onChange={(event) => setApprovalId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={approvePlan}>
            Aprobar
          </button>{" "}
          <button className="primary" onClick={startPlan}>
            Iniciar
          </button>{" "}
          <button className="primary" onClick={evaluatePlan}>
            Evaluar
          </button>
        </p>
        {planError && <ErrorState message={planError} />}

        <h4>Capturar seguimiento (fixture)</h4>
        <label>
          Ingreso neto observado
          <br />
          <input value={netRevenue} onChange={(event) => setNetRevenue(event.target.value)} />
        </label>{" "}
        <label>
          Margen bruto observado
          <br />
          <input value={grossMargin} onChange={(event) => setGrossMargin(event.target.value)} />
        </label>{" "}
        <label>
          % margen bruto observado
          <br />
          <input value={grossMarginPercent} onChange={(event) => setGrossMarginPercent(event.target.value)} />
        </label>{" "}
        <label>
          Versión de definición de métrica
          <br />
          <input value={metricDefinitionVersion} onChange={(event) => setMetricDefinitionVersion(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={captureFollowup}>
            Capturar seguimiento
          </button>
        </p>
        {captureError && <ErrorState message={captureError} />}
      </div>

      <div className="card">
        <h3>3. Informe de resultado realizado</h3>
        <label>
          Report ID
          <br />
          <input value={reportId} onChange={(event) => setReportId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={loadReport}>
            Consultar informe
          </button>
        </p>
        {reportError && <ErrorState message={reportError} />}
        {report && (
          <div>
            <p>
              Clasificación: <StatusBadge status={report.result_classification} />
            </p>
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th>Estimado (conservador)</th>
                  <th>Estimado (base)</th>
                  <th>Estimado (optimista)</th>
                  <th>Observado</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Valor</td>
                  <td>{report.estimated_conservative}</td>
                  <td>{report.estimated_base}</td>
                  <td>{report.estimated_optimistic}</td>
                  <td>{report.observed_margin_change ?? "--"}</td>
                </tr>
              </tbody>
            </table>
            <p>
              Valor realizado: <strong>{report.realized_value ?? "--"}</strong>
            </p>
            <Disclaimer />
            <p>
              Coste de implementación: {report.implementation_cost ?? "no evidenciado"} -- Net ROI:{" "}
              <strong>{report.net_realized_value ?? "no calculado (sin coste evidenciado)"}</strong>
            </p>
            <Disclaimer />
            {report.limitations.length > 0 && (
              <p>Limitaciones: {report.limitations.join(", ")}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
