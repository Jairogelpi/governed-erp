import { useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import { StatusBadge } from "../components/StatusBadge";

interface RequiredFieldRow {
  fieldName: string;
  fieldType: string;
}

const EMPTY_REQUIRED_FIELD: RequiredFieldRow = { fieldName: "", fieldType: "string" };

export function Capabilities() {
  const [name, setName] = useState("");
  const [connectionId, setConnectionId] = useState("");
  const [operation, setOperation] = useState<"update_field" | "create_record" | "archive_record">("update_field");
  const [targetModel, setTargetModel] = useState("");
  const [targetField, setTargetField] = useState("");
  const [fieldType, setFieldType] = useState("string");
  const [minimumValue, setMinimumValue] = useState("");
  const [maximumValue, setMaximumValue] = useState("");
  const [allowedValues, setAllowedValues] = useState("");
  const [maxRecordsPerRun, setMaxRecordsPerRun] = useState("1");
  const [requiredFields, setRequiredFields] = useState<RequiredFieldRow[]>([{ ...EMPTY_REQUIRED_FIELD }]);
  const [idempotencyField, setIdempotencyField] = useState("");
  const [declareError, setDeclareError] = useState<string | null>(null);

  const [modelFields, setModelFields] = useState<Array<{ name: string; type: string; readonly: boolean }>>([]);
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [schemaLoading, setSchemaLoading] = useState(false);

  async function loadModelFields() {
    if (!connectionId || !targetModel) return;
    setSchemaError(null);
    setSchemaLoading(true);
    const { data, error } = await api.GET(
      "/v1/connectors/{connector_id}/connections/{connection_id}/schema/{model}",
      { params: { path: { connector_id: "odoo", connection_id: connectionId, model: targetModel } } },
    );
    setSchemaLoading(false);
    if (error) {
      setSchemaError("No se pudo consultar el esquema real de ese modelo (revisa la conexión y el nombre del modelo).");
      setModelFields([]);
      return;
    }
    setModelFields(data.fields.filter((field) => !field.readonly));
  }

  const [items, setItems] = useState<
    Array<{
      id: string;
      name: string;
      operation: string;
      target_model: string;
      target_field: string | null;
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
    const requiredFieldsPayload =
      operation === "create_record"
        ? Object.fromEntries(
            requiredFields.filter((row) => row.fieldName.trim()).map((row) => [row.fieldName.trim(), row.fieldType]),
          )
        : undefined;
    const { error } = await api.POST("/v1/declared-capabilities", {
      body: {
        name,
        target_model: targetModel,
        operation,
        target_field: operation === "update_field" ? targetField : undefined,
        field_type: operation === "update_field" ? fieldType : undefined,
        minimum_value: operation === "update_field" ? minimumValue || undefined : undefined,
        maximum_value: operation === "update_field" ? maximumValue || undefined : undefined,
        allowed_values:
          operation === "update_field" && allowedValues
            ? allowedValues.split(",").map((value) => value.trim())
            : undefined,
        required_fields: requiredFieldsPayload,
        idempotency_field: operation === "create_record" ? idempotencyField || undefined : undefined,
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
    setRequiredFields([{ ...EMPTY_REQUIRED_FIELD }]);
    setIdempotencyField("");
    await loadCapabilities();
  }

  function updateRequiredField(index: number, patch: Partial<RequiredFieldRow>) {
    setRequiredFields((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)));
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
          Connection ID (para consultar el esquema real)
          <br />
          <input value={connectionId} onChange={(event) => setConnectionId(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Operación
          <br />
          <select value={operation} onChange={(event) => setOperation(event.target.value as typeof operation)}>
            <option value="update_field">Actualizar campo (uno o varios registros)</option>
            <option value="create_record">Crear registro (idempotente)</option>
            <option value="archive_record">
              Archivar registro (active=False, siempre reversible -- nunca borrado físico)
            </option>
          </select>
        </label>
        <br />
        <label>
          Modelo Odoo (técnico)
          <br />
          <input value={targetModel} onChange={(event) => setTargetModel(event.target.value)} placeholder="res.partner" />
        </label>{" "}
        {operation !== "archive_record" && (
          <>
            <button type="button" className="primary" onClick={loadModelFields} disabled={schemaLoading}>
              Consultar campos reales
            </button>
            {schemaError && <ErrorState message={schemaError} />}
          </>
        )}
        <br />

        {operation === "update_field" && (
          <>
            <label>
              Campo (técnico)
              <br />
              {modelFields.length > 0 ? (
                <select value={targetField} onChange={(event) => setTargetField(event.target.value)}>
                  <option value="">-- selecciona un campo --</option>
                  {modelFields.map((field) => (
                    <option key={field.name} value={field.name}>
                      {field.name} ({field.type})
                    </option>
                  ))}
                </select>
              ) : (
                <input value={targetField} onChange={(event) => setTargetField(event.target.value)} placeholder="loyalty_discount_pct" />
              )}
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
              Máx. registros por ejecución (permite operar en lote)
              <br />
              <input value={maxRecordsPerRun} onChange={(event) => setMaxRecordsPerRun(event.target.value)} />
            </label>
          </>
        )}

        {operation === "create_record" && (
          <>
            <h4>Campos requeridos (se deben enviar exactamente estos, ni más ni menos)</h4>
            {requiredFields.map((row, index) => (
              <div key={index}>
                <label>
                  Campo
                  <input
                    value={row.fieldName}
                    onChange={(event) => updateRequiredField(index, { fieldName: event.target.value })}
                    placeholder="name"
                  />
                </label>{" "}
                <label>
                  Tipo
                  <select
                    value={row.fieldType}
                    onChange={(event) => updateRequiredField(index, { fieldType: event.target.value })}
                  >
                    <option value="string">string</option>
                    <option value="integer">integer</option>
                    <option value="decimal">decimal</option>
                    <option value="boolean">boolean</option>
                  </select>
                </label>
              </div>
            ))}
            <p>
              <button
                type="button"
                className="primary"
                onClick={() => setRequiredFields((prev) => [...prev, { ...EMPTY_REQUIRED_FIELD }])}
              >
                Añadir campo
              </button>
            </p>
            <label>
              Campo de idempotencia (debe ser uno de los campos requeridos -- evita duplicados en reintentos)
              <br />
              <input value={idempotencyField} onChange={(event) => setIdempotencyField(event.target.value)} placeholder="name" />
            </label>
          </>
        )}

        {operation === "archive_record" && (
          <p>Esta capacidad siempre archiva (`active=False`); nunca ejecuta un borrado físico.</p>
        )}
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
              <th>Operación</th>
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
                <td>{item.operation}</td>
                <td>
                  {item.target_model}
                  {item.target_field ? `.${item.target_field}` : ""}
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
