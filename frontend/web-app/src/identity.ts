export type Role = "cliente" | "organizador";
export type WebSession = { access_token: string; csrf_token: string; expires_in: number };
export type RoleAssignment = { role: string; status: string };
export type Account = { account_id: string; email: string; roles: RoleAssignment[] };
export type Organizer = { account_id: string; email: string; status: string };
export type OrganizerStatus = "habilitado" | "deshabilitado";

export class IdentityError extends Error {
  constructor(public readonly status: number) {
    super("Identity request failed");
  }
}

function identityUrl(path: string): string {
  const configured = import.meta.env.VITE_IDENTITY_ORIGIN;
  if (!configured) return path;
  const url = new URL(configured);
  if (!(["https:", "http:"].includes(url.protocol)) || url.username || url.password || url.pathname !== "/" || url.search || url.hash) {
    throw new Error("Invalid Identity origin");
  }
  if (url.protocol === "http:" && !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)) {
    throw new Error("Identity origin requires HTTPS outside local development");
  }
  return `${url.origin}${path}`;
}

async function post(path: string, body: object): Promise<Response> {
  const response = await fetch(identityUrl(path), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new IdentityError(response.status);
  return response;
}

export async function register(email: string, password: string, role: Role): Promise<void> {
  await post("/auth/register", { email, password, role });
}

export async function login(email: string, password: string): Promise<WebSession> {
  const response = await post("/auth/web/login", { email, password });
  return response.json() as Promise<WebSession>;
}

export async function readCsrf(): Promise<string> {
  const response = await fetch(identityUrl("/auth/web/csrf"), { credentials: "include", cache: "no-store" });
  if (!response.ok) throw new IdentityError(response.status);
  return ((await response.json()) as { csrf_token: string }).csrf_token;
}

export async function refreshSession(csrf: string): Promise<WebSession> {
  const response = await fetch(identityUrl("/auth/web/refresh"), { method: "POST", credentials: "include", headers: { "X-CSRF-Token": csrf } });
  if (!response.ok) throw new IdentityError(response.status);
  const tokens = await response.json() as Omit<WebSession, "csrf_token">;
  return { ...tokens, csrf_token: csrf };
}

export async function logoutSession(csrf: string): Promise<void> {
  const response = await fetch(identityUrl("/auth/web/logout"), { method: "POST", credentials: "include", headers: { "X-CSRF-Token": csrf } });
  if (!response.ok) throw new IdentityError(response.status);
}

export async function getAccount(token: string, signal: AbortSignal): Promise<Account> {
  const response = await fetch(identityUrl("/auth/me"), { credentials: "include", headers: { Authorization: `Bearer ${token}` }, signal });
  if (!response.ok) throw new IdentityError(response.status);
  return response.json() as Promise<Account>;
}

export async function getOrganizers(token: string, signal: AbortSignal): Promise<Organizer[]> {
  const response = await fetch(identityUrl("/admin/organizers"), { credentials: "include", headers: { Authorization: `Bearer ${token}` }, signal });
  if (!response.ok) throw new IdentityError(response.status);
  return response.json() as Promise<Organizer[]>;
}

export async function setOrganizerStatus(token: string, id: string, status: OrganizerStatus): Promise<{ account_id: string; status: OrganizerStatus }> {
  const response = await fetch(identityUrl(`/admin/organizers/${encodeURIComponent(id)}/status`), {
    method: "PATCH", credentials: "include", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ status }),
  });
  if (!response.ok) throw new IdentityError(response.status);
  return response.json() as Promise<{ account_id: string; status: OrganizerStatus }>;
}

export async function requestRole(token: string, role: Role): Promise<RoleAssignment[]> {
  const response = await fetch(identityUrl("/auth/me/roles"), {
    method: "POST",
    credentials: "include",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });
  if (!response.ok) throw new IdentityError(response.status);
  const result = await response.json() as { roles: RoleAssignment[] };
  return result.roles;
}
