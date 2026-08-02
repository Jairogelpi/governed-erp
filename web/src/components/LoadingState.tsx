export function LoadingState({ label = "Cargando..." }: { label?: string }) {
  return <p role="status">{label}</p>;
}
