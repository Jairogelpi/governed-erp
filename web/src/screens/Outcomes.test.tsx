import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Outcomes } from "./Outcomes";
import { CAUSAL_DISCLAIMER_TEXT } from "../components/Disclaimer";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Outcomes", () => {
  it("renders the causal-confidence disclaimer next to realized-value numbers", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({
          id: "outcomereport_1",
          estimated_conservative: "100.00",
          estimated_base: "200.00",
          estimated_optimistic: "300.00",
          observed_revenue_change: "150.00",
          observed_margin_change: "150.00",
          realized_value: "150.00",
          implementation_cost: "50.00",
          net_realized_value: "100.00",
          result_classification: "positive_observed_result",
          limitations: ["observed_change_is_not_a_causal_claim"],
        }),
      ),
    );

    render(
      <MemoryRouter>
        <Outcomes />
      </MemoryRouter>,
    );

    const reportIdInput = screen.getAllByRole("textbox").at(-1)!;
    fireEvent.change(reportIdInput, { target: { value: "outcomereport_1" } });
    fireEvent.click(screen.getByText("Consultar informe"));

    await waitFor(() => {
      expect(screen.getAllByText(CAUSAL_DISCLAIMER_TEXT).length).toBeGreaterThanOrEqual(2);
    });
  });
});
