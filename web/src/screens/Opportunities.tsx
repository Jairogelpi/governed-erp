import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import { StatusBadge } from "../components/StatusBadge";

interface MarginOpportunity {
  id: string;
  cause: string;
  affected_population: string[];
  impact_conservative: string;
  impact_base: string;
  impact_optimistic: string;
  confidence_band: string;
  risk_level: string;
  proposed_action: string;
  status: string;
}

export function Opportunities() {
  const navigate = useNavigate();
  const [marginAnalysisId, setMarginAnalysisId] = useState("");
  const [opportunities, setOpportunities] = useState<MarginOpportunity[] | null>(null);
  const [blocked, setBlocked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  async function listOpportunities() {
    setError(null);
    setOpportunities(null);
    const { data, error: apiError } = await api.GET("/v1/margin-analyses/{margin_analysis_id}/opportunities", {
      params: { path: { margin_analysis_id: marginAnalysisId } },
    });
    if (apiError) {
      setError("No se encontró ese análisis de margen.");
      return;
    }
    setOpportunities(data.opportunities as MarginOpportunity[]);
    setBlocked(data.blocked);
  }

  async function generateOpportunities() {
    setError(null);
    const { data, error: apiError } = await api.POST("/v1/margin-analyses/{margin_analysis_id}/opportunities", {
      params: { path: { margin_analysis_id: marginAnalysisId } },
      body: {},
    });
    if (apiError) {
      setError("No se pudieron generar oportunidades para ese análisis.");
      return;
    }
    setOpportunities(data.opportunities as MarginOpportunity[]);
    setBlocked(data.blocked);
  }

  return (
    <div>
      <h2>Oportunidades</h2>
      <div className="card">
        <label>
          Margin analysis ID
          <br />
          <input value={marginAnalysisId} onChange={(event) => setMarginAnalysisId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={listOpportunities}>
            Listar oportunidades
          </button>{" "}
          <button className="primary" onClick={generateOpportunities}>
            Generar oportunidades
          </button>
        </p>
        {error && <ErrorState message={error} />}
        {blocked && <ErrorState message="El análisis de margen subyacente está bloqueado; las oportunidades pueden estar incompletas." />}
      </div>

      {opportunities && (
        <div className="card">
          {opportunities.length === 0 && <p>No hay oportunidades para este análisis.</p>}
          {opportunities.map((opportunity) => (
            <div key={opportunity.id} className="card">
              <p>
                <strong>{opportunity.cause}</strong> -- <StatusBadge status={opportunity.risk_level} />{" "}
                <StatusBadge status={opportunity.status} />
              </p>
              <button
                className="primary"
                onClick={() => setExpanded(expanded === opportunity.id ? null : opportunity.id)}
              >
                {expanded === opportunity.id ? "Ocultar detalle" : "Ver detalle"}
              </button>{" "}
              <button className="primary" onClick={() => navigate("/recommendations", { state: { opportunityId: opportunity.id } })}>
                Crear recomendación
              </button>
              {expanded === opportunity.id && (
                <div>
                  <p>Población afectada: {opportunity.affected_population.join(", ") || "--"}</p>
                  <p>
                    Impacto conservador / base / optimista: {opportunity.impact_conservative} /{" "}
                    {opportunity.impact_base} / {opportunity.impact_optimistic}
                  </p>
                  <p>Banda de confianza: {opportunity.confidence_band}</p>
                  <p>Acción propuesta: {opportunity.proposed_action}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
