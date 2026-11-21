import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.e2e.js",
  use: { baseURL: "http://localhost:15174", browserName: "chromium" },
  reporter: "list",
});
