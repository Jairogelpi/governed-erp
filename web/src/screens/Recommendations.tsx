import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import { JsonBlock } from "../components/JsonBlock";
import { StatusBadge } from "../components/StatusBadge";

interface PricingLine {
  product_id: string;
  quantity: string;
  proposed_unit_price: string;
  cost_reference: string;
  minimum_margin_percent: string;
}

const EMPTY_LINE: PricingLine = {
  product_id: "",
  quantity: "1",
  proposed_unit_price: "0",
  cost_reference: "0",
  minimum_margin_percent: "0",
};

export function Recommendations() {
  const location = useLocation() as { state?: { opportunityId?: string } };

  // Create
  const [opportunityId, setOpportunityId] = useState(location.state?.opportunityId ?? "");
  const [recommendationType, setRecommendationType] = useState("pricing_scenario");
  const [title, setTitle] = useState("");
  const [selectedActionTemplate, setSelectedActionTemplate] = useState("pricing_scenario_v1");
  const [createError, setCreateError] = useState<string | null>(null);

  // Lifecycle
  const [recommendationId, setRecommendationId] = useState("");
  const [recommendation, setRecommendation] = useState<{
    id: string;
    status: string;
    approval_scope: string;
    content_hash: string;
  } | null>(null);
  const [recommendationError, setRecommendationError] = useState<string | null>(null);
  const [approvalId, setApprovalId] = useState("");

  useEffect(() => {
    if (location.state?.opportunityId) setOpportunityId(location.state.opportunityId);
  }, [location.state]);

  // Action draft
  const [processKey, setProcessKey] = useState("");
  const [connectionId, setConnectionId] = useState("");
  const [partnerId, setPartnerId] = useState("1");
  const [companyId, setCompanyId] = useState("1");
  const [currencyId, setCurrencyId] = useState("1");
  const [pricelistId, setPricelistId] = useState("1");
  const [lines, setLines] = useState<PricingLine[]>([{ ...EMPTY_LINE }]);
  const [actionDraft, setActionDraft] = useState<{ id: string; status: string } | null>(null);
  const [actionDraftError, setActionDraftError] = useState<string | null>(null);
  const [actionDraftDetail, setActionDraftDetail] = useState<unknown>(null);
  const [routeThroughCanary, setRouteThroughCanary] = useState(false);
  const [businessObjectKey, setBusinessObjectKey] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [planRunError, setPlanRunError] = useState<string | null>(null);

  async function createRecommendation() {
    setCreateError(null);
    const { data, error } = await api.POST("/v1/opportunities/{opportunity_id}/recommendations", {
      params: { path: { opportunity_id: opportunityId } },
      body: { recommendation_type: recommendationType, title, selected_action_template: selectedActionTemplate },
    });
    if (error) {
      setCreateError("No se pudo crear la recomendación (revisa que la oportunidad exista y no esté bloqueada).");
      return;
    }
    setRecommendation(data);
    setRecommendationId(data.id);
  }

  async function loadRecommendation() {
    setRecommendationError(null);
    const { data, error } = await api.GET("/v1/recommendations/{recommendation_id}", {
      params: { path: { recommendation_id: recommendationId } },
    });
    if (error) {
      setRecommendationError("No se encontró la recomendación.");
      return;
    }
    setRecommendation(data);
  }

  async function submitRecommendation() {
    setRecommendationError(null);
    const { data, error } = await api.POST("/v1/recommendations/{recommendation_id}/submit", {
      params: { path: { recommendation_id: recommendationId } },
    });
    if (error) {
      setRecommendationError("No se pudo enviar la recomendación.");
      return;
    }
    setRecommendation(data);
  }

  async function approveRecommendation() {
    setRecommendationError(null);
    const { data, error } = await api.POST("/v1/recommendations/{recommendation_id}/approve", {
      params: { path: { recommendation_id: recommendationId } },
      body: { approval_id: approvalId },
    });
    if (error) {
      setRecommendationError(
        "No se pudo aprobar (recuerda: el aprobador debe ser distinto de quien creó la recomendación).",
      );
      return;
    }
    setRecommendation(data);
  }

  async function rejectRecommendation() {
    setRecommendationError(null);
    const { data, error } = await api.POST("/v1/recommendations/{recommendation_id}/reject", {
      params: { path: { recommendation_id: recommendationId } },
    });
    if (error) {
      setRecommendationError("No se pudo rechazar la recomendación.");
      return;
    }
    setRecommendation(data);
  }

  function updateLine(index: number, patch: Partial<PricingLine>) {
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  }

  async function createActionDraft() {
    setActionDraftError(null);
    const { data, error } = await api.POST("/v1/recommendations/{recommendation_id}/action-drafts", {
      params: { path: { recommendation_id: recommendationId } },
      body: {
        process_key: processKey,
        connection_id: connectionId || undefined,
        pricing_inputs: {
          partner_id: Number(partnerId),
          company_id: Number(companyId),
          currency_id: Number(currencyId),
          pricelist_id: Number(pricelistId),
          lines: lines.map((line) => ({
            product_id: Number(line.product_id),
            quantity: Number(line.quantity),
            proposed_unit_price: line.proposed_unit_price,
            cost_reference: line.cost_reference,
            minimum_margin_percent: line.minimum_margin_percent,
          })),
        },
      },
    });
    if (error) {
      setActionDraftError("No se pudo crear el borrador de acción.");
      return;
    }
    setActionDraft({ id: data.id, status: data.status });
  }

  async function validateActionDraft() {
    if (!actionDraft) return;
    setActionDraftError(null);
    const { data, error } = await api.POST("/v1/action-drafts/{action_draft_id}/validate", {
      params: { path: { action_draft_id: actionDraft.id } },
    });
    if (error) {
      setActionDraftError("El borrador no pasó la validación (preflight).");
      return;
    }
    setActionDraft({ id: data.id, status: data.status });
    setActionDraftDetail(data);
  }

  async function planRunActionDraft() {
    if (!actionDraft) return;
    setPlanRunError(null);
    const { data, error } = await api.POST("/v1/action-drafts/{action_draft_id}/plan-run", {
      params: { path: { action_draft_id: actionDraft.id } },
      body: {
        idempotency_key: idempotencyKey,
        routing_context: routeThroughCanary
          ? { business_object_key: businessObjectKey }
          : undefined,
      },
    });
    if (error) {
      setPlanRunError("La planificación de la ejecución fue rechazada (revisa los problemas de preflight).");
      return;
    }
    setActionDraft({ id: data.id, status: data.status });
    setActionDraftDetail(data);
  }

  return (
    <div>
      <h2>Recomendaciones</h2>

      <div className="card">
        <h3>Crear recomendación</h3>
        <label>
          Opportunity ID
          <br />
          <input value={opportunityId} onChange={(event) => setOpportunityId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Tipo
          <br />
          <input value={recommendationType} onChange={(event) => setRecommendationType(event.target.value)} />
        </label>{" "}
        <label>
          Título
          <br />
          <input value={title} onChange={(event) => setTitle(event.target.value)} style={{ width: "60%" }} />
        </label>
        <br />
        <label>
          Plantilla de acción seleccionada
          <br />
          <input value={selectedActionTemplate} onChange={(event) => setSelectedActionTemplate(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={createRecommendation}>
            Crear
          </button>
        </p>
        {createError && <ErrorState message={createError} />}
      </div>

      <div className="card">
        <h3>Ciclo de vida</h3>
        <label>
          Recommendation ID
          <br />
          <input value={recommendationId} onChange={(event) => setRecommendationId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={loadRecommendation}>
            Consultar
          </button>{" "}
          <button className="primary" onClick={submitRecommendation}>
            Enviar
          </button>
        </p>
        <label>
          Approval ID (debe pertenecer a un actor distinto del creador)
          <br />
          <input value={approvalId} onChange={(event) => setApprovalId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <p>
          <button className="primary" onClick={approveRecommendation}>
            Aprobar
          </button>{" "}
          <button className="primary" onClick={rejectRecommendation}>
            Rechazar
          </button>
        </p>
        {recommendationError && <ErrorState message={recommendationError} />}
        {recommendation && (
          <div>
            <p>
              Estado: <StatusBadge status={recommendation.status} />
            </p>
            <p>
              Ámbito de aprobación (lo que firma el aprobador, literal): <code>{recommendation.approval_scope}</code>
            </p>
            <p>
              Content hash: <code>{recommendation.content_hash}</code>
            </p>
          </div>
        )}
      </div>

      <div className="card">
        <h3>Borrador de acción (pricing scenario)</h3>
        <label>
          Process key
          <br />
          <input value={processKey} onChange={(event) => setProcessKey(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Connection ID
          <br />
          <input value={connectionId} onChange={(event) => setConnectionId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Partner ID
          <br />
          <input value={partnerId} onChange={(event) => setPartnerId(event.target.value)} />
        </label>{" "}
        <label>
          Company ID
          <br />
          <input value={companyId} onChange={(event) => setCompanyId(event.target.value)} />
        </label>{" "}
        <label>
          Currency ID
          <br />
          <input value={currencyId} onChange={(event) => setCurrencyId(event.target.value)} />
        </label>{" "}
        <label>
          Pricelist ID
          <br />
          <input value={pricelistId} onChange={(event) => setPricelistId(event.target.value)} />
        </label>

        <h4>Líneas</h4>
        {lines.map((line, index) => (
          <div key={index}>
            <label>
              Producto
              <input value={line.product_id} onChange={(event) => updateLine(index, { product_id: event.target.value })} />
            </label>{" "}
            <label>
              Cantidad
              <input value={line.quantity} onChange={(event) => updateLine(index, { quantity: event.target.value })} />
            </label>{" "}
            <label>
              Precio propuesto
              <input
                value={line.proposed_unit_price}
                onChange={(event) => updateLine(index, { proposed_unit_price: event.target.value })}
              />
            </label>{" "}
            <label>
              Coste de referencia
              <input value={line.cost_reference} onChange={(event) => updateLine(index, { cost_reference: event.target.value })} />
            </label>{" "}
            <label>
              Margen mínimo %
              <input
                value={line.minimum_margin_percent}
                onChange={(event) => updateLine(index, { minimum_margin_percent: event.target.value })}
              />
            </label>
          </div>
        ))}
        <p>
          <button className="primary" onClick={() => setLines((prev) => [...prev, { ...EMPTY_LINE }])}>
            Añadir línea
          </button>
        </p>

        <p>
          <button className="primary" onClick={createActionDraft}>
            Crear borrador
          </button>{" "}
          <button className="primary" onClick={validateActionDraft} disabled={!actionDraft}>
            Validar
          </button>
        </p>
        {actionDraftError && <ErrorState message={actionDraftError} />}
        {actionDraft && (
          <p>
            Draft <strong>{actionDraft.id}</strong> -- <StatusBadge status={actionDraft.status} />
          </p>
        )}

        <h4>Ejecutar (plan-run)</h4>
        <label>
          Idempotency key
          <br />
          <input value={idempotencyKey} onChange={(event) => setIdempotencyKey(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          <input type="checkbox" checked={routeThroughCanary} onChange={(event) => setRouteThroughCanary(event.target.checked)} />{" "}
          Enrutar por canary
        </label>
        {routeThroughCanary && (
          <>
            <br />
            <label>
              Business object key
              <br />
              <input value={businessObjectKey} onChange={(event) => setBusinessObjectKey(event.target.value)} style={{ width: "100%" }} />
            </label>
          </>
        )}
        <p>
          <button className="primary" onClick={planRunActionDraft} disabled={!actionDraft}>
            Planificar ejecución
          </button>
        </p>
        {planRunError && <ErrorState message={planRunError} />}
        {actionDraftDetail !== null && <JsonBlock value={actionDraftDetail} />}
      </div>
    </div>
  );
}
