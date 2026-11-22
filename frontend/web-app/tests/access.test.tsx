import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../src/App";

vi.mock("../src/sessionCoordinator", async () => {
  const identity = await import("../src/identity");
  return { SessionCoordinator: class {
    restore() { return Promise.reject(new identity.IdentityError(401)); }
    async signIn(email: string, password: string) { return { ...await identity.login(email, password), generation: "test" }; }
    close() { /* No shared resources in this test. */ }
  } };
});

async function renderApp() {
  render(<App />);
  await screen.findByRole("button", { name: "Ingresar" });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("access forms", () => {
  it("validates input before sending a registration", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    await renderApp();
    await user.click(screen.getByRole("button", { name: "Crear cuenta" }));
    await user.type(screen.getByLabelText("Email"), "invalid");
    await user.type(screen.getByLabelText("Contraseña"), "short");
    await user.click(screen.getByRole("button", { name: "Registrarse" }));
    expect(screen.getByRole("alert").textContent).toContain("al menos 8 caracteres");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("registers an organizer and returns to login without the password", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    await renderApp();
    await user.click(screen.getByRole("button", { name: "Crear cuenta" }));
    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Contraseña"), "password123");
    await user.selectOptions(screen.getByLabelText("Tipo de cuenta"), "organizador");
    await user.click(screen.getByRole("button", { name: "Registrarse" }));
    expect(screen.getByRole("status").textContent).toContain("pendiente");
    expect((screen.getByLabelText("Contraseña") as HTMLInputElement).value).toBe("");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ email: "user@example.com", password: "password123", role: "organizador" });
  });

  it("registers a client and shows progress while waiting", async () => {
    let finish!: (value: { ok: boolean }) => void;
    vi.stubGlobal("fetch", vi.fn(() => new Promise((resolve) => { finish = resolve; })));
    const user = userEvent.setup();
    await renderApp();
    await user.click(screen.getByRole("button", { name: "Crear cuenta" }));
    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Contraseña"), "password123");
    await user.click(screen.getByRole("button", { name: "Registrarse" }));
    expect((screen.getByRole("button", { name: "Procesando..." }) as HTMLButtonElement).disabled).toBe(true);
    finish({ ok: true });
    expect((await screen.findByRole("status")).textContent).toContain("Cuenta creada");
  });

  it("reports network failures without presenting an authenticated session", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    const user = userEvent.setup();
    await renderApp();
    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Contraseña"), "password123");
    await user.click(screen.getByRole("button", { name: "Ingresar" }));
    expect((await screen.findByRole("alert")).textContent).toContain("servicio");
    expect(screen.queryByText("Sesión iniciada.")).toBeNull();
  });

  it.each([
    ["register", 409, "ya está registrado"],
    ["login", 401, "credenciales"],
    ["login", 503, "servicio"],
    ["register", 400, "datos ingresados"],
  ])("shows a useful %s error for HTTP %i", async (mode, status, message) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status }));
    const user = userEvent.setup();
    await renderApp();
    if (mode === "register") await user.click(screen.getByRole("button", { name: "Crear cuenta" }));
    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Contraseña"), "password123");
    await user.click(screen.getByRole("button", { name: mode === "login" ? "Ingresar" : "Registrarse" }));
    expect((await screen.findByRole("alert")).textContent).toContain(message);
  });

  it("logs in and keeps the access token out of browser storage", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({ ok: true, json: async () => ({ access_token: "access-secret", csrf_token: "csrf", expires_in: 600 }) }).mockResolvedValue({ ok: true, json: async () => ({ account_id: "1", email: "user@example.com", roles: [] }) }));
    const user = userEvent.setup();
    await renderApp();
    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Contraseña"), "password123");
    await user.click(screen.getByRole("button", { name: "Ingresar" }));
    expect((await screen.findByText("Email: user@example.com")).textContent).toBe("Email: user@example.com");
    expect(JSON.stringify(localStorage)).not.toContain("access-secret");
    expect(JSON.stringify(sessionStorage)).not.toContain("access-secret");
  });
});
