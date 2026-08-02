import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Canary } from "./Canary";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Canary", () => {
  it("renders the `recommend` field as an advisory banner, not a clickable action", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({
          status: "active",
          stable_case_count: 10,
          canary_case_count: 2,
          success_count: 2,
          blocked_count: 0,
          failed_count: 0,
          cumulative_amount: 500,
          unexpected_side_effect_count: 0,
          estimated_opportunity_value: "120.00",
          recommend: "continue_canary",
        }),
      ),
    );

    render(
      <MemoryRouter>
        <Canary />
      </MemoryRouter>,
    );

    const textboxes = screen.getAllByRole("textbox");
    // 9th text input on the page is Policy ID (see Canary.tsx field order).
    fireEvent.change(textboxes[8], { target: { value: "canarypolicy_abc" } });
    fireEvent.click(screen.getByText("Ver dashboard"));

    await waitFor(() => {
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    const banner = screen.getByRole("status");
    expect(banner).toHaveTextContent(/Recomendación asesora/i);
    expect(banner).toHaveTextContent("continue_canary");
    expect(banner.tagName).not.toBe("BUTTON");
    expect(banner.querySelector("button")).toBeNull();
  });
});
