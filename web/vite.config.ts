/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    manifest: true,
  },
  server: {
    proxy: {
      "/v1": "http://127.0.0.1:8000",
      "/internal": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    // e2e/ holds Playwright specs (run via `npm run e2e`), not Vitest ones.
    exclude: ["node_modules/**", "e2e/**"],
  },
});
