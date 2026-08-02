import createClient from "openapi-fetch";
import type { paths } from "./schema";

const TOKEN_STORAGE_KEY = "erpguard.token";

export function getToken(): string | null {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setToken(token: string | null): void {
  if (token) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

const baseUrl = typeof window !== "undefined" ? window.location.origin : "http://localhost";

// `fetch` is wrapped instead of passed by reference so it resolves
// `globalThis.fetch` at call time -- tests stub the global after this
// module has already been imported and `createClient` has run.
export const api = createClient<paths>({
  baseUrl,
  fetch: (...args: Parameters<typeof globalThis.fetch>) => globalThis.fetch(...args),
});

api.use({
  onRequest({ request }) {
    const token = getToken();
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
});
