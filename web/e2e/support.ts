import type { APIRequestContext, Page } from "@playwright/test";

const TOKEN_STORAGE_KEY = "erpguard.token";

export async function bootstrapAuthenticatedPage(
  page: Page,
  request: APIRequestContext,
  options: { tenantId: string; roleName?: "admin" | "operator" | "viewer" },
): Promise<string> {
  const response = await request.post("/internal/dev-tokens", {
    data: {
      tenant_id: options.tenantId,
      role_name: options.roleName ?? "admin",
      display_name: "Playwright E2E",
    },
  });
  if (!response.ok()) {
    throw new Error(
      "Dev-token bootstrap failed -- start the backend with ERPGUARD_INTERNAL_SURFACES=true " +
        `(HTTP ${response.status()}).`,
    );
  }
  const body = (await response.json()) as { token: string };

  await page.goto("/settings");
  await page.evaluate(
    ({ key, token }) => window.localStorage.setItem(key, token),
    { key: TOKEN_STORAGE_KEY, token: body.token },
  );
  return body.token;
}
