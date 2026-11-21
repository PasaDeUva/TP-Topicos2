import { test, expect } from "@playwright/test";
import { randomUUID } from "node:crypto";

test("logout rejects the previous token and clears other tabs", async ({ page, context, request }) => {
  const base = process.env.E2E_BASE_URL ?? "http://localhost:15174";
  const email = `${randomUUID()}@example.com`;
  const registration = await request.post(`${base}/auth/register`, { data: { email, password: "password123", role: "cliente" } });
  expect(registration.status()).toBe(201);
  await page.goto(base);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Contraseña").fill("password123");
  const login = page.waitForResponse((response) => response.url().endsWith("/auth/web/login") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Ingresar" }).click();
  const token = (await (await login).json()).access_token;
  await expect(page.getByText(`Email: ${email}`)).toBeVisible();
  const second = await context.newPage();
  await second.goto(base);
  await expect(second.getByText(`Email: ${email}`)).toBeVisible();
  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page.getByText("Sesión cerrada.")).toBeVisible();
  await expect(second.getByText("La sesión no es válida. Inicie sesión nuevamente.")).toBeVisible();
  const denied = await request.get(`${base}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
  expect(denied.status()).toBe(401);
});
