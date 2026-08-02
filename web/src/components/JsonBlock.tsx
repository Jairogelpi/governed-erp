export function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: "0.8rem" }}>
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
