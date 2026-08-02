import { useEffect, useState } from "react";
import { api } from "../api/client";
import { LoadingState } from "../components/LoadingState";
import { ErrorState } from "../components/ErrorState";
import { DataTable } from "../components/DataTable";

interface ConnectorDefinition {
  connector_id: string;
  display_name: string;
  vendor: string;
  system_types: string[];
  capabilities: { name: string; safety_tier: string }[];
}

interface UnifiedConnection {
  id: string;
  name: string;
  connector_type: string;
  status: string;
}

export function Connections() {
  const [connectors, setConnectors] = useState<ConnectorDefinition[] | null>(null);
  const [connections, setConnections] = useState<UnifiedConnection[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connectionId, setConnectionId] = useState("");
  const [connectorId, setConnectorId] = useState("");
  const [testResult, setTestResult] = useState<string | null>(null);

  // Create connection
  const [newName, setNewName] = useState("");
  const [newConnectorType, setNewConnectorType] = useState("fake");
  const [newEndpoint, setNewEndpoint] = useState("fake://local");
  const [newSecret, setNewSecret] = useState("fake-secret");
  const [createError, setCreateError] = useState<string | null>(null);
  const [created, setCreated] = useState<UnifiedConnection | null>(null);

  // Ingest fake events
  const [ingestError, setIngestError] = useState<string | null>(null);
  const [ingestResult, setIngestResult] = useState<string | null>(null);

  async function refresh() {
    const [connectorsResult, connectionsResult] = await Promise.all([
      api.GET("/v1/connectors"),
      api.GET("/v1/connections"),
    ]);
    if (!connectorsResult.error) setConnectors(connectorsResult.data as ConnectorDefinition[]);
    if (!connectionsResult.error) setConnections(connectionsResult.data as UnifiedConnection[]);
  }

  async function createConnection() {
    setCreateError(null);
    setCreated(null);
    const { data, error: apiError } = await api.POST("/v1/connections", {
      body: {
        name: newName,
        connector_type: newConnectorType,
        endpoint: newEndpoint,
        auth_type: "api_key",
        secret: newSecret,
      },
    });
    if (apiError) {
      setCreateError("No se pudo crear la conexión.");
      return;
    }
    setCreated(data as UnifiedConnection);
    setConnectionId(data.id);
    await refresh();
  }

  async function ingestFakeEvents() {
    setIngestError(null);
    setIngestResult(null);
    const { data, error: apiError } = await api.POST("/v1/events/fake-generate");
    if (apiError) {
      setIngestError("No se pudieron generar eventos de ejemplo.");
      return;
    }
    setIngestResult(
      `Ingeridos ${data.created_events} eventos y ${data.created_objects} objetos (fuente: fake-generator).`,
    );
  }

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.GET("/v1/connectors"), api.GET("/v1/connections")]).then(
      ([connectorsResult, connectionsResult]) => {
        if (cancelled) return;
        if (connectorsResult.error || connectionsResult.error) {
          setError("No se pudieron cargar los conectores o las conexiones.");
          return;
        }
        setConnectors((connectorsResult.data ?? []) as ConnectorDefinition[]);
        setConnections((connectionsResult.data ?? []) as UnifiedConnection[]);
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  async function testConnector() {
    setTestResult(null);
    if (!connectorId || !connectionId) return;
    const { data, error: apiError } = await api.POST("/v1/connectors/{connector_id}/test", {
      params: { path: { connector_id: connectorId } },
      body: { connection_id: connectionId },
    });
    if (apiError) {
      setTestResult(`Error: ${JSON.stringify(apiError)}`);
      return;
    }
    setTestResult(`${data.status}: ${data.summary}`);
  }

  if (error) return <ErrorState message={error} />;
  if (!connectors || !connections) return <LoadingState />;

  return (
    <div>
      <h2>Conexiones</h2>
      <div className="card">
        <h3>Conectores disponibles</h3>
        <DataTable
          rows={connectors}
          rowKey={(row) => row.connector_id}
          columns={[
            { key: "id", header: "ID", render: (row) => row.connector_id },
            { key: "name", header: "Nombre", render: (row) => row.display_name },
            { key: "vendor", header: "Fabricante", render: (row) => row.vendor },
            { key: "caps", header: "Capacidades", render: (row) => row.capabilities.length },
          ]}
        />
      </div>
      <div className="card">
        <h3>Conexiones configuradas</h3>
        <DataTable
          rows={connections}
          rowKey={(row) => row.id}
          columns={[
            { key: "id", header: "ID", render: (row) => row.id },
            { key: "name", header: "Nombre", render: (row) => row.name },
            { key: "type", header: "Tipo", render: (row) => row.connector_type },
            { key: "status", header: "Estado", render: (row) => row.status },
          ]}
        />
      </div>
      <div className="card">
        <h3>Conectar (nueva conexión)</h3>
        <label>
          Nombre
          <br />
          <input value={newName} onChange={(event) => setNewName(event.target.value)} style={{ width: "100%" }} />
        </label>
        <br />
        <label>
          Tipo de conector
          <br />
          <input value={newConnectorType} onChange={(event) => setNewConnectorType(event.target.value)} />
        </label>{" "}
        <label>
          Endpoint
          <br />
          <input value={newEndpoint} onChange={(event) => setNewEndpoint(event.target.value)} />
        </label>{" "}
        <label>
          Secreto
          <br />
          <input value={newSecret} onChange={(event) => setNewSecret(event.target.value)} type="password" />
        </label>
        <p>
          <button className="primary" onClick={createConnection}>
            Crear conexión
          </button>
        </p>
        {createError && <ErrorState message={createError} />}
        {created && (
          <p className="badge badge-ok">
            Conexión creada: {created.id} ({created.status})
          </p>
        )}
      </div>

      <div className="card">
        <h3>Ingerir (eventos de ejemplo)</h3>
        <p>Genera un lote determinista de eventos OCEL desde el conector Fake ERP para explorar variantes.</p>
        <p>
          <button className="primary" onClick={ingestFakeEvents}>
            Ingerir eventos de ejemplo
          </button>
        </p>
        {ingestError && <ErrorState message={ingestError} />}
        {ingestResult && <p>{ingestResult}</p>}
      </div>

      <div className="card">
        <h3>Probar conexión</h3>
        <label>
          Connector ID
          <br />
          <input value={connectorId} onChange={(event) => setConnectorId(event.target.value)} />
        </label>
        <br />
        <label>
          Connection ID
          <br />
          <input value={connectionId} onChange={(event) => setConnectionId(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={testConnector}>
            Probar
          </button>
        </p>
        {testResult && <p>{testResult}</p>}
      </div>
    </div>
  );
}
