import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Settings } from "./Settings";
import { setToken } from "../api/client";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

beforeEach(() => {
  setToken(null);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Settings", () => {
  it("validates a pasted token against /v1/identity/me", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ user_id: "u1", tenant_id: "t1", role_name: "viewer" })),
    );
    render(
      <MemoryRouter>
        <Settings />
      </MemoryRouter>,
    );
    fireEvent.change(document.querySelector("textarea")!, {
      target: { value: "some-token" },
    });
    fireEvent.click(screen.getByText("Guardar token"));
    await waitFor(() => {
      expect(screen.getByText(/Validado: u1/)).toBeInTheDocument();
    });
  });

  it("shows a graceful message when the dev-token bootstrap is not mounted", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not found", { status: 404 })));
    render(
      <MemoryRouter>
        <Settings />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Generar token de desarrollo" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/no está disponible/i);
    });
  });

  it("stores the generated token on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({
          token: "dev-token-abc",
          user_id: "dev-user-1",
          tenant_id: "demo-tenant",
          role_name: "admin",
          expires_in_seconds: 3600,
        }),
      ),
    );
    render(
      <MemoryRouter>
        <Settings />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Generar token de desarrollo" }));
    await waitFor(() => {
      expect(screen.getByText(/Validado: dev-user-1/)).toBeInTheDocument();
    });
  });
});
