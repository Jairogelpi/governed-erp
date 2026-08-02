import { defineConfig } from "@playwright/test";

/**
 * Spec 94 E2E: exercises the built frontend against a real running
 * backend (Fake connector only, no live Odoo). Not wired into the
 * `frontend` CI job -- standing up Postgres/the full app stack there is
 * disproportionate for a TFM-scope product; this is a documented manual
 * verification path (see web/e2e/README.md), run locally with:
 *
 *   uvicorn apps.api.main:app --port 8000   # ERPGUARD_INTERNAL_SURFACES=true
 *   cd web && npm run build && npx playwright install --with-deps chromium
 *   npm run e2e
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.ERPGUARD_E2E_BASE_URL ?? "http://127.0.0.1:8000",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
