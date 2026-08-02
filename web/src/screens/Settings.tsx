import { useState } from "react";
import { useLocation } from "react-router-dom";
import { api, getToken, setToken } from "../api/client";
import { ErrorState } from "../components/ErrorState";

interface DevTokenResponse {
  token: string;
  user_id: string;
  tenant_id: string;
  role_name: string;
  expires_in_seconds: number;
}

export function Settings() {
  const location = useLocation() as { state?: { reason?: string } };
  const [pasted, setPasted] = useState(getToken() ?? "");
  const [validated, setValidated] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [tenantId, setTenantId] = useState("demo-tenant");
  const [roleName, setRoleName] = useState("admin");
  const [displayName, setDisplayName] = useState("Dev user");
  const [devTokenError, setDevTokenError] = useState<string | null>(null);
  const [devTokenBusy, setDevTokenBusy] = useState(false);

  async function saveToken() {
    setToken(pasted || null);
    setError(null);
    const { data, error: apiError } = await api.GET("/v1/identity/me");
    if (apiError) {
      setError("El token no es válido o no se pudo verificar.");
      setValidated(null);
      return;
    }
    setValidated(`${data.user_id} (${data.tenant_id} / ${data.role_name})`);
  }

  async function generateDevToken() {
    setDevTokenBusy(true);
    setDevTokenError(null);
    try {
      const response = await fetch("/internal/dev-tokens", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tenant_id: tenantId, role_name: roleName, display_name: displayName }),
      });
      if (!response.ok) {
        setDevTokenError(
          response.status === 404
            ? "El bootstrap de tokens de desarrollo no está disponible en este despliegue " +
              "(requiere ERPGUARD_INTERNAL_SURFACES=true)."
            : `No se pudo generar el token (HTTP ${response.status}).`,
        );
        return;
      }
      const body = (await response.json()) as DevTokenResponse;
      setPasted(body.token);
      setToken(body.token);
      setValidated(`${body.user_id} (${body.tenant_id} / ${body.role_name})`);
    } catch {
      setDevTokenError("No se pudo contactar con el backend.");
    } finally {
      setDevTokenBusy(false);
    }
  }

  return (
    <div>
      <h2>Ajustes</h2>
      {location.state?.reason === "auth_required" && (
        <ErrorState message="Se requiere un token de sesión para acceder a esa pantalla." />
      )}
      <div className="card">
        <h3>Token de sesión</h3>
        <p>
          Pega un token Bearer existente, o genera uno de desarrollo abajo (solo
          disponible cuando el backend expone superficies internas).
        </p>
        <textarea
          value={pasted}
          onChange={(event) => setPasted(event.target.value)}
          rows={3}
          style={{ width: "100%" }}
        />
        <p>
          <button className="primary" onClick={saveToken}>
            Guardar token
          </button>
        </p>
        {error && <ErrorState message={error} />}
        {validated && <p className="badge badge-ok">Validado: {validated}</p>}
      </div>
      <div className="card">
        <h3>Generar token de desarrollo</h3>
        <label>
          Tenant
          <br />
          <input value={tenantId} onChange={(event) => setTenantId(event.target.value)} />
        </label>
        <br />
        <label>
          Rol
          <br />
          <select value={roleName} onChange={(event) => setRoleName(event.target.value)}>
            <option value="admin">admin</option>
            <option value="operator">operator</option>
            <option value="viewer">viewer</option>
          </select>
        </label>
        <br />
        <label>
          Nombre
          <br />
          <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
        </label>
        <p>
          <button className="primary" onClick={generateDevToken} disabled={devTokenBusy}>
            {devTokenBusy ? "Generando..." : "Generar token de desarrollo"}
          </button>
        </p>
        {devTokenError && <ErrorState message={devTokenError} />}
      </div>
    </div>
  );
}
