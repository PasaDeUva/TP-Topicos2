// @vitest-environment node
import { createServer as createHttpServer, type Server as HttpServer } from "node:http";
import { afterEach, expect, it, vi } from "vitest";
import { createServer as createViteServer, type ViteDevServer } from "vite";

let upstream: HttpServer | undefined;
let vite: ViteDevServer | undefined;

afterEach(async () => {
  await vite?.close();
  if (upstream?.listening) await new Promise<void>((resolve, reject) => upstream!.close((error) => error ? reject(error) : resolve()));
  vite = undefined;
  upstream = undefined;
  vi.unstubAllEnvs();
});

it("proxies authentication and administration to the configured Identity target", async () => {
  upstream = createHttpServer((request, response) => { response.writeHead(200); response.end(request.url); });
  await new Promise<void>((resolve) => upstream!.listen(0, "127.0.0.1", resolve));
  const upstreamAddress = upstream.address();
  if (!upstreamAddress || typeof upstreamAddress === "string") throw new Error("Upstream address unavailable");
  vi.stubEnv("IDENTITY_PROXY_TARGET", `http://127.0.0.1:${upstreamAddress.port}`);
  vite = await createViteServer({ server: { host: "127.0.0.1", port: 0 }, logLevel: "silent" });
  await vite.listen();
  const viteAddress = vite.httpServer?.address();
  if (!viteAddress || typeof viteAddress === "string") throw new Error("Vite address unavailable");
  for (const path of ["/auth/me", "/admin/organizers"]) {
    const response = await fetch(`http://127.0.0.1:${viteAddress.port}${path}`);
    expect(response.status).toBe(200);
    expect(await response.text()).toBe(path);
  }
});
