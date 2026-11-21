import { afterEach, expect, it, vi } from "vitest";
import { getAccount, getOrganizers, setOrganizerStatus, login, logoutSession, readCsrf, refreshSession, register, requestRole } from "../src/identity";

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

it("sends organizer operations with the access token and propagates authorization errors", async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [] }).mockResolvedValueOnce({ ok: true, json: async () => ({ account_id: "id", status: "habilitado" }) }).mockResolvedValueOnce({ ok: false, status: 403 });
  vi.stubGlobal("fetch", fetchMock);
  const signal = new AbortController().signal;
  await getOrganizers("token", signal);
  await setOrganizerStatus("token", "id", "habilitado");
  await expect(getOrganizers("token", signal)).rejects.toMatchObject({ status: 403 });
  expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe("Bearer token");
  expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "PATCH", headers: { Authorization: "Bearer token" }, body: JSON.stringify({ status: "habilitado" }) });
});

it("sends all Identity operations to the configured origin with credentials", async () => {
  vi.stubEnv("VITE_IDENTITY_ORIGIN", "https://identity.example.com");
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ csrf_token: "csrf", roles: [] }) });
  vi.stubGlobal("fetch", fetchMock);
  await register("user@example.com", "password123", "cliente");
  await login("user@example.com", "password123");
  await readCsrf();
  await refreshSession("csrf");
  await logoutSession("csrf");
  await getAccount("token", new AbortController().signal);
  await requestRole("token", "organizador");
  expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
    "https://identity.example.com/auth/register", "https://identity.example.com/auth/web/login",
    "https://identity.example.com/auth/web/csrf", "https://identity.example.com/auth/web/refresh",
    "https://identity.example.com/auth/web/logout", "https://identity.example.com/auth/me",
    "https://identity.example.com/auth/me/roles",
  ]);
  expect(fetchMock.mock.calls.every(([, options]) => options.credentials === "include")).toBe(true);
});

it.each(["http://identity.example.com", "https://identity.example.com/path", "https://user:password@identity.example.com"])("rejects unsafe Identity origin %s", async (origin) => {
  vi.stubEnv("VITE_IDENTITY_ORIGIN", origin);
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  await expect(login("user@example.com", "password123")).rejects.toThrow();
  expect(fetchMock).not.toHaveBeenCalled();
});
