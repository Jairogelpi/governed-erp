import type { ReactNode } from "react";

export const CAUSAL_DISCLAIMER_TEXT =
  "Este cambio observado no constituye una afirmación causal " +
  "(observed_change_is_not_a_causal_claim): el resultado medido puede " +
  "reflejar otros factores además de la recomendación aplicada.";

export function Disclaimer({ children }: { children?: ReactNode }) {
  return <p className="disclaimer">{children ?? CAUSAL_DISCLAIMER_TEXT}</p>;
}
