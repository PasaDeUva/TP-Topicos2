import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { mkdtempSync, mkdirSync, readFileSync, rmSync } from "node:fs";
import http from "node:http";
import https from "node:https";
import path from "node:path";

test.skip(process.env.E2E_HTTPS !== "1", "Requires an isolated HTTPS-configured Identity stack");
test.use({ ignoreHTTPSErrors: true });

test("HTTPS cookie, CSRF, origins and credential confidentiality", async ({ page, context, request }) => {
  const parent = path.join(process.cwd(), "test-results");
  mkdirSync(parent, { recursive: true });
  const temp = mkdtempSync(path.join(parent, "tls-"));
  const key = path.join(temp, "key.pem");
  const cert = path.join(temp, "cert.pem");
  let server;
  try {
    execFileSync("openssl", ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", cert, "-days", "1", "-subj", "/CN=localhost"], { stdio: "ignore" });
    server = https.createServer({ key: readFileSync(key), cert: readFileSync(cert) }, (incoming, outgoing) => {
      const upstream = http.request({ hostname: "127.0.0.1", port: 15174, path: incoming.url, method: incoming.method, headers: incoming.headers }, (response) => {
        outgoing.writeHead(response.statusCode, response.headers);
        response.pipe(outgoing);
      });
      upstream.on("error", () => { outgoing.writeHead(502); outgoing.end(); });
      incoming.pipe(upstream);
    });
    await new Promise((resolve) => server.listen(15443, "127.0.0.1", resolve));
    const origin = "https://localhost:15443";
    const email = `${randomUUID()}@example.com`;
    await page.goto(origin);
    await page.getByRole("button", { name: "Crear cuenta" }).click();
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Contraseña").fill("password123");
    await page.getByRole("button", { name: "Registrarse" }).click();
    await expect(page.getByRole("status")).toContainText("Cuenta creada");
    await page.getByLabel("Contraseña").fill("password123");
    const loginResponse = page.waitForResponse((response) => response.url().endsWith("/auth/web/login"));
    await page.getByRole("button", { name: "Ingresar" }).click();
    const body = await (await loginResponse).text();
    await expect(page.getByText(`Email: ${email}`)).toBeVisible();
    const cookie = (await context.cookies()).find((item) => item.name === "identity_refresh");
    expect(cookie).toMatchObject({ domain: "localhost", httpOnly: true, sameSite: "Strict", secure: true, path: "/auth/web" });
    expect(body).not.toContain(cookie.value);
    const result = await page.evaluate(async () => {
      const csrf = await (await fetch("/auth/web/csrf")).json();
      const invalid = await fetch("/auth/web/refresh", { method: "POST", headers: { "X-CSRF-Token": "invalid" } });
      return { csrf: csrf.csrf_token, status: invalid.status, storage: JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }) };
    });
    expect(result.status).toBe(403);
    expect(result.storage).not.toContain(cookie.value);
    const denied = await request.post(`${origin}/auth/web/refresh`, { headers: { Origin: "https://evil.example.com", Cookie: `identity_refresh=${cookie.value}`, "X-CSRF-Token": result.csrf } });
    expect(denied.status()).toBe(403);
    const untrusted = await context.newPage();
    await untrusted.goto("https://127.0.0.1:15443");
    const crossOriginReadable = await untrusted.evaluate(async (url) => {
      try { await fetch(`${url}/auth/web/csrf`, { credentials: "include" }); return true; } catch { return false; }
    }, origin);
    expect(crossOriginReadable).toBe(false);
    await untrusted.close();
    const refreshResponse = page.waitForResponse((response) => response.url().endsWith("/auth/web/refresh"));
    await page.reload();
    await expect(page.getByText(`Email: ${email}`)).toBeVisible();
    const refreshBody = await (await refreshResponse).text();
    const rotated = (await context.cookies()).find((item) => item.name === "identity_refresh");
    expect(refreshBody).not.toContain(cookie.value);
    expect(refreshBody).not.toContain(rotated.value);
    const rotatedStorage = await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }));
    expect(rotatedStorage).not.toContain(rotated.value);
    const logs = execFileSync("docker", ["compose", "-p", process.env.E2E_COMPOSE_PROJECT, "logs", "--no-color", "identity-service"], { encoding: "utf8" });
    expect(logs).not.toContain(cookie.value);
    expect(logs).not.toContain(rotated.value);
  } finally {
    if (server) {
      server.closeAllConnections();
      await new Promise((resolve) => server.close(resolve));
    }
    rmSync(temp, { recursive: true, force: true });
  }
});
