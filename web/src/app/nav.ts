export interface NavItem {
  path: string;
  label: string;
}

export const NAV_ITEMS: NavItem[] = [
  { path: "/", label: "Resumen" },
  { path: "/connections", label: "Conexiones" },
  { path: "/processes", label: "Procesos" },
  { path: "/replays", label: "Replays" },
  { path: "/deployments", label: "Despliegues" },
  { path: "/opportunities", label: "Oportunidades" },
  { path: "/recommendations", label: "Recomendaciones" },
  { path: "/canary", label: "Canary" },
  { path: "/runs", label: "Ejecuciones" },
  { path: "/outcomes", label: "Resultados" },
  { path: "/evidence", label: "Evidencia" },
  { path: "/benchmarks", label: "Benchmarks" },
  { path: "/settings", label: "Ajustes" },
];
