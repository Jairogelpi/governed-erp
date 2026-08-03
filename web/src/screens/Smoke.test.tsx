import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Connections } from "./Connections";
import { Processes } from "./Processes";
import { Replays } from "./Replays";
import { Deployments } from "./Deployments";
import { Runs } from "./Runs";
import { Opportunities } from "./Opportunities";
import { Recommendations } from "./Recommendations";
import { Evidence } from "./Evidence";
import { Benchmarks } from "./Benchmarks";
import { Capabilities } from "./Capabilities";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("form-driven screens render without crashing", () => {
  it("Connections loads connectors and connections on mount", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(jsonResponse([]))));
    render(
      <MemoryRouter>
        <Connections />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Conexiones configuradas")).toBeInTheDocument();
    });
  });

  it.each([
    ["Processes", Processes, "Procesos"],
    ["Replays", Replays, "Replays"],
    ["Deployments", Deployments, "Despliegues"],
    ["Runs", Runs, "Ejecuciones"],
    ["Opportunities", Opportunities, "Oportunidades"],
    ["Recommendations", Recommendations, "Recomendaciones"],
    ["Evidence", Evidence, "Evidencia"],
    ["Benchmarks", Benchmarks, "Benchmarks (ERPRiskBench)"],
    ["Capabilities", Capabilities, "Capacidades de escritura declaradas"],
  ] as const)("%s renders its heading without a backend call", (_name, Component, heading) => {
    render(
      <MemoryRouter>
        <Component />
      </MemoryRouter>,
    );
    expect(screen.getByText(heading)).toBeInTheDocument();
  });
});
