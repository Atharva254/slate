import { defineConfig } from "@playwright/test";
import path from "node:path";

const python = path.resolve(
  "..",
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);

export default defineConfig({
  testDir: "./tests",
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5174",
    viewport: { width: 1360, height: 1100 },
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `"${python}" -m uvicorn backend.tests.browser_server:app --app-dir .. --host 127.0.0.1 --port 8001`,
      url: "http://127.0.0.1:8001/health",
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --port 5174",
      url: "http://127.0.0.1:5174",
      env: { API_PROXY_TARGET: "http://127.0.0.1:8001" },
      reuseExistingServer: false,
    },
  ],
});
