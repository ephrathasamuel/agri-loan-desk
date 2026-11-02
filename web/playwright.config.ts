import { defineConfig, devices } from "@playwright/test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// End-to-end tests start their own API (fresh SQLite database, throwaway
// admin) and the built Next.js app, then drive them in Chromium.
// Creating an assessment downloads real NASA POWER data, so it needs internet.
const API_PORT = 8010;
const WEB_PORT = 3010;
const apiDir = path.resolve(__dirname, "../api");
const venvPython = path.join(apiDir, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const python = process.env.PYTHON ?? (fs.existsSync(venvPython) ? venvPython : "python");
const dbFile = path.join(os.tmpdir(), `agri-loan-e2e-${Date.now()}.db`).replace(/\\/g, "/");

export const E2E_ADMIN = {
  email: process.env.E2E_ADMIN_EMAIL ?? "e2e-admin@example.com",
  password: process.env.E2E_ADMIN_PASSWORD ?? "e2e-password-123",
};

export default defineConfig({
  testDir: "./e2e",
  timeout: 180_000,
  expect: { timeout: 15_000 },
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    // Use the installed Chrome locally; CI installs Playwright's Chromium.
    ...(process.env.CI ? {} : { channel: "chrome" }),
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], ...(process.env.CI ? {} : { channel: "chrome" }) } },
  ],
  webServer: [
    {
      command: `"${python}" -m uvicorn app.main:app --port ${API_PORT}`,
      cwd: apiDir,
      url: `http://127.0.0.1:${API_PORT}/health`,
      reuseExistingServer: false,
      timeout: 240_000,
      env: {
        DATABASE_URL: `sqlite:///${dbFile}`,
        SECRET_KEY: process.env.SECRET_KEY ?? "e2e-only-secret-key",
        ADMIN_EMAIL: E2E_ADMIN.email,
        ADMIN_PASSWORD: E2E_ADMIN.password,
        ADMIN_NAME: "E2E Admin",
        ANTHROPIC_API_KEY: "",
      },
    },
    {
      command: `npm run start -- --port ${WEB_PORT}`,
      url: `http://127.0.0.1:${WEB_PORT}/login`,
      reuseExistingServer: false,
      timeout: 240_000,
      env: { API_URL: `http://127.0.0.1:${API_PORT}`, INSECURE_COOKIES: "1" },
    },
  ],
});
