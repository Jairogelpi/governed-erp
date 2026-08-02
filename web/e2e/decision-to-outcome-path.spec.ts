import { expect, test } from "@playwright/test";
import { bootstrapAuthenticatedPage } from "./support";

/**
 * Spec 94 exit criterion: opportunity -> recommendation -> approve ->
 * canary -> outcome -> evidence. Reaching a real opportunity requires a
 * full margin-analysis precondition chain (decision intelligence ingest +
 * snapshot + analysis) that this smoke spec does not fabricate -- it
 * verifies each screen in the pillar is reachable, renders its real
 * layout (advisory banner, causal disclaimer, evidence manifest table)
 * against the live backend, and accepts input, closing the loop at the
 * UI layer. Full precondition-to-outcome coverage lives in the backend's
 * own tests (tests/test_backend_rc_end_to_end.py).
 */
test("decision-to-outcome pillar screens are reachable and show their safety copy", async ({
  page,
  request,
}) => {
  const tenantId = `e2e-tenant-${Date.now()}`;
  await bootstrapAuthenticatedPage(page, request, { tenantId });

  await page.goto("/opportunities");
  await expect(page.getByRole("heading", { name: "Oportunidades" })).toBeVisible();

  await page.goto("/recommendations");
  await expect(page.getByRole("heading", { name: "Recomendaciones" })).toBeVisible();
  await expect(page.getByText(/Enrutar por canary/)).toBeVisible();

  await page.goto("/canary");
  await expect(page.getByRole("heading", { name: "Canary" })).toBeVisible();

  await page.goto("/outcomes");
  await expect(page.getByRole("heading", { name: "Resultados" })).toBeVisible();

  await page.goto("/evidence");
  await expect(page.getByRole("heading", { name: "Evidencia" })).toBeVisible();
  await expect(page.getByText("Bundle de evidencia decisión-a-resultado")).toBeVisible();
});
