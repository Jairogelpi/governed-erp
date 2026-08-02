const OK_STATUSES = new Set([
  "active",
  "approved",
  "completed",
  "complete",
  "sealed",
  "executed",
  "success",
  "positive_observed_result",
  "eligible_for_promotion",
  "connected",
  "ok",
]);

const WARN_STATUSES = new Set([
  "pending",
  "pending_approval",
  "draft",
  "submitted",
  "planned",
  "building",
  "started",
  "ready",
  "continue_canary",
  "not_enough_evidence",
  "inconclusive",
  "neutral_observed_result",
]);

const DANGER_STATUSES = new Set([
  "rejected",
  "blocked",
  "blocked_incomplete_data",
  "blocked_pending_approval",
  "failed",
  "aborted",
  "revoked",
  "invalidated",
  "pause_and_investigate",
  "abort",
  "negative_observed_result",
  "incomplete",
  "critical",
  "high",
]);

function toneFor(status: string): string {
  const key = status.toLowerCase();
  if (OK_STATUSES.has(key)) return "badge-ok";
  if (WARN_STATUSES.has(key)) return "badge-warn";
  if (DANGER_STATUSES.has(key)) return "badge-danger";
  return "badge-muted";
}

export function StatusBadge({ status }: { status: string | null | undefined }) {
  if (!status) return <span className="badge badge-muted">--</span>;
  return <span className={`badge ${toneFor(status)}`}>{status}</span>;
}
