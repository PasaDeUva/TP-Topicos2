import { test, expect } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

test.skip(process.env.E2E_UPGRADE !== "1", "Requires the dedicated isolated upgrade environment.");

test("restores an existing browser session after the Identity upgrade", async ({ page, context, request }) => {
  const project = "tp-revocacion-e2e-2026";
  const root = process.env.E2E_COMPOSE_ROOT;
  if (process.env.E2E_COMPOSE_PROJECT !== project || !root) throw new Error("Dedicated isolated project is required");
  const base = "http://localhost:25174";
  const email = `${randomUUID()}@example.com`;
  const registered = await request.post(`${base}/auth/register`, { data: { email, password: "password123", role: "cliente" } });
  expect(registered.status()).toBe(201);
  await page.goto(base);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Contraseña").fill("password123");
  const login = page.waitForResponse((response) => response.url().endsWith("/auth/web/login") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Ingresar" }).click();
  const legacyToken = (await (await login).json()).access_token;
  await expect(page.getByText(`Email: ${email}`)).toBeVisible();
  execFileSync("docker", ["compose", "-p", project, "-f", "compose.yaml", "up", "-d", "--no-deps", "--no-build", "--force-recreate", "--wait", "identity-service"], { cwd: resolve(root), stdio: "ignore" });
  expect((await request.get(`${base}/auth/me`, { headers: { Authorization: `Bearer ${legacyToken}` } })).status()).toBe(401);
  await page.reload();
  await expect(page.getByText(`Email: ${email}`)).toBeVisible();
  const second = await context.newPage();
  await second.goto(base);
  await expect(second.getByText(`Email: ${email}`)).toBeVisible();
});
