import { test, expect } from "@playwright/test";
import { randomUUID } from "node:crypto";

test.skip(process.env.E2E_ROLLBACK !== "1", "Requires an isolated deployment of the previous Identity version.");

test("previous Identity accepts its access token after browser logout", async ({ page, request }) => {
  const base = process.env.E2E_BASE_URL ?? "http://localhost:15174";
  const email = `${randomUUID()}@example.com`;
  expect((await request.post(`${base}/auth/register`, { data: { email, password: "password123", role: "cliente" } })).status()).toBe(201);
  await page.goto(base);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Contraseña").fill("password123");
  const login = page.waitForResponse((response) => response.url().endsWith("/auth/web/login") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Ingresar" }).click();
  const token = (await (await login).json()).access_token;
  await expect(page.getByText(`Email: ${email}`)).toBeVisible();
  const logout = page.waitForResponse((response) => response.url().endsWith("/auth/web/logout") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  expect((await logout).status()).toBe(204);
  expect((await request.get(`${base}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })).status()).toBe(200);
});
