import { test, expect } from "@playwright/test";
import { randomUUID } from "node:crypto";

test("administrator manages an organizer while a regular user has no panel", async ({ page, browser, request }) => {
  const email = `${randomUUID()}@example.com`;
  const registration = await request.post("/auth/register", { data: { email, password: "password123", role: "organizador" } });
  expect(registration.status()).toBe(201);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Contraseña").fill("password123");
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByText("organizador: pendiente")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Administrar organizadores" })).toHaveCount(0);

  const adminContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
  try {
    const adminPage = await adminContext.newPage();
    await adminPage.goto("http://localhost:15174/");
    await adminPage.getByLabel("Email").fill("admin@example.com");
    await adminPage.getByLabel("Contraseña").fill("local-admin-password");
    await adminPage.getByRole("button", { name: "Ingresar" }).click();
    await expect(adminPage.getByRole("heading", { name: "Administrar organizadores" })).toBeVisible();
    await adminPage.getByRole("button", { name: `Habilitar ${email}` }).click();
    await expect(adminPage.getByRole("button", { name: `Deshabilitar ${email}` })).toBeVisible();
    await page.reload();
    await expect(page.getByText("organizador: habilitado")).toBeVisible();
    await adminPage.getByRole("button", { name: `Deshabilitar ${email}` }).click();
    await expect(adminPage.getByRole("button", { name: `Habilitar ${email}` })).toBeVisible();
    expect(await adminPage.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  } finally {
    await adminContext.close();
  }
});
