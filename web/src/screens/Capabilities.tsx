import { useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import { StatusBadge } from "../components/StatusBadge";

export function Capabilities() {
  const [name, setName] = useState("");
  const [targetModel, setTargetModel] = useState("");
  const [targetField, setTargetField] = useState("");
  const [fieldType, setFieldType] = useState("string");
  const [minimumValue, setMinimumValue] = useState("");
  const [maximumValue, setMaximumValue] = useState("");
  const [allowedValues, setAllowedValues] = useState("");
  const [maxRecordsPerRun, setMaxRecordsPerRun] = useState("1");
  const [declareError, setDeclareError] = useState<string | null>(null);

  const [items, setItems] = useState<
    Array<{
      id: string;
      name: string;
      target_model: string;
      target_field: string;
      status: string;
      approval_scope: string;
      created_by: string;
    }>
  >([]);
  const [listError, setListError] = useState<string | null>(null);

  const [approvalId, setApprovalId] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  async function loadCapabilities() {
    setListError(null);
    const { data, error } = await api.GET("/v1/declared-capabilities");
    if (error) {
      setListError("No se pudieron cargar las capacidades declaradas.");
      return;
    }
    setItems(data.items);
  }

  async function declareCapability() {
    setDeclareError(null);
    const { error } = await api.POST("/v1/declared-capabilities", {
      body: {
        name,
        target_model: targetModel,
        target_field: targetField,
        field_type: fieldType,
        minimum_value: minimumValue || undefined,
        maximum_value: maximumValue || undefined,
        allowed_values: allowedValues
          ? allowedValues.split(",").map((value) => value.trim())
          : undefined,
        max_records_per_run: Number(maxRecordsPerRun),
      },
    });
    if (error) {
      setDeclareError("No se pudo declarar la capacidad (revisa la lista de denegación de modelo/campo).");
      return;
    }
    setName("");
    setTargetModel("");
    setTargetField("");
    await loadCapabilities();
  }

  async function approveCapability(capabilityId: string) {
    setActionError(null);
    const { error } = await api.POST("/v1/declared-capabilities/{capability_id}/approve", {
      params: { path: { capability_id: capabilityId } },
      body: { approval_id: approvalId },
    });
    if (error) {
      setActionError("No se pudo aprobar (el aprobador debe ser distinto de quien declaró la capacidad).");
      return;
    }
    await loadCapabilities();
  }

  async function activateCapability(capabilityId: string) {
    setActionError(null);
    const { error } = await api.POST("/v1/declared-capabilities/{capability_id}/activate", {
      params: { path: { capability_id: capabilityId } },
    });
    if (error) {
      setActionError("No se pudo activar la capacidad.");
      return;
    }
    await loadCapabilities();
  }

  return (
    <div>
      <h2>Capacidades de escritura declaradas</h2>
      <p>
        Declara un campo de escritura acotado (modelo + campo + tipo + rango) sin necesidad de
        desplegar código. Cada capacidad debe ser aprobada por un usuario distinto de quien la
        declaró y activada antes de poder usarse en una ejecución real.
      </p>

      <div className="card">
        <h3>Declarar nueva capacidad</h3>
        <label>
          Nombre
          <br />
          <input value={name} onChange={(event) => setName(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Modelo Odoo (técnico)
          <br />
          <input value={targetModel} onChange={(event) => setTargetModel(event.target.value)} placeholder="res.partner" />
        </label>{" "}
        <label>
          Campo (técnico)
          <br />
          <input value={targetField} onChange={(event) => setTargetField(event.target.value)} placeholder="loyalty_discount_pct" />
        </label>{" "}
        <label>
          Tipo
          <br />
          <select value={fieldType} onChange={(event) => setFieldType(event.target.value)}>
            <option value="string">string</option>
            <option value="integer">integer</option>
            <option value="decimal">decimal</option>
            <option value="boolean">boolean</option>
          </select>
        </label>
        <br />
        <label>
          Mínimo
          <br />
          <input value={minimumValue} onChange={(event) => setMinimumValue(event.target.value)} />
        </label>{" "}
        <label>
          Máximo
          <br />
          <input value={maximumValue} onChange={(event) => setMaximumValue(event.target.value)} />
        </label>{" "}
        <label>
          Valores permitidos (separados por comas)
          <br />
          <input value={allowedValues} onChange={(event) => setAllowedValues(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Máx. registros por ejecución
          <br />
          <input value={maxRecordsPerRun} onChange={(event) => setMaxRecordsPerRun(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={declareCapability}>
            Declarar
          </button>
        </p>
        {declareError && <ErrorState message={declareError} />}
      </div>

      <div className="card">
        <h3>Capacidades declaradas</h3>
        <p>
          <button className="primary" onClick={loadCapabilities}>
            Actualizar lista
          </button>
        </p>
        <label>
          Approval ID (para aprobar una capacidad de la lista)
          <br />
          <input value={approvalId} onChange={(event) => setApprovalId(event.target.value)} style={{ width: "100%" }} />
        </label>
        {listError && <ErrorState message={listError} />}
        {actionError && <ErrorState message={actionError} />}
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Objetivo</th>
              <th>Estado</th>
              <th>Creado por</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.name}</td>
                <td>
                  {item.target_model}.{item.target_field}
                </td>
                <td>
                  <StatusBadge status={item.status} />
                </td>
                <td>{item.created_by}</td>
                <td>
                  {item.status === "draft" && (
                    <button className="primary" onClick={() => approveCapability(item.id)}>
                      Aprobar
                    </button>
                  )}
                  {item.status === "approved" && (
                    <button className="primary" onClick={() => activateCapability(item.id)}>
                      Activar
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
