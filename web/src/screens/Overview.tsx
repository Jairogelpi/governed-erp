import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { LoadingState } from "../components/LoadingState";
import { ErrorState } from "../components/ErrorState";
import { NAV_ITEMS } from "../app/nav";

interface CurrentUser {
  user_id: string;
  tenant_id: string;
  role_name: string;
}

export function Overview() {
  const [me, setMe] = useState<CurrentUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.GET("/v1/identity/me").then(({ data, error: apiError }) => {
      if (cancelled) return;
      if (apiError) {
        setError("No se pudo cargar la identidad actual.");
      } else if (data) {
        setMe(data as CurrentUser);
      }
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <h2>Resumen</h2>
      <div className="card">
        {loading && <LoadingState />}
        {error && <ErrorState message={error} />}
        {me && (
          <p>
            Conectado como <strong>{me.user_id}</strong> en el tenant{" "}
            <strong>{me.tenant_id}</strong> con rol <strong>{me.role_name}</strong>.
          </p>
        )}
      </div>
      <div className="card">
        <h3>Camino operativo</h3>
        <p>
          conectar → ingerir → inspeccionar variantes → replay del candidato →
          inspeccionar prueba → compilar → ejecutar
        </p>
        <h3>Camino de decisión a resultado</h3>
        <p>
          oportunidad → recomendación → aprobación → borrador de acción →
          ejecución (opcionalmente por canary) → resultado medido → evidencia sellada
        </p>
      </div>
      <div className="card">
        <h3>Navegación</h3>
        <ul>
          {NAV_ITEMS.filter((item) => item.path !== "/").map((item) => (
            <li key={item.path}>
              <Link to={item.path}>{item.label}</Link>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
