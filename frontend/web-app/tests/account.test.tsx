import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AccountView from "../src/AccountView";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("account roles", () => {
  it("shows administration only to an active administrator", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => ({ account_id: "123", email: "admin@example.com", roles: [{ role: "administrador", status: "activo" }] }) }).mockResolvedValueOnce({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    render(<AccountView token="token" onInvalidSession={vi.fn()} />);
    expect(await screen.findByRole("heading", { name: "Administrar organizadores" })).toBeTruthy();
    expect(await screen.findByText(/No hay organizadores/)).toBeTruthy();
  });

  it("does not request the administrative list for a client", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ account_id: "123", email: "user@example.com", roles: [{ role: "cliente", status: "activo" }] }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<AccountView token="token" onInvalidSession={vi.fn()} />);
    expect(await screen.findByText("cliente: activo")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Administrar organizadores" })).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it("shows progress while requesting a role and the resulting status", async () => {
    let finish!: (value: object) => void;
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ account_id: "123", email: "user@example.com", roles: [{ role: "cliente", status: "activo" }] }) })
      .mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; })));
    const user = userEvent.setup();
    render(<AccountView token="token" onInvalidSession={vi.fn()} />);
    await user.click(await screen.findByRole("button", { name: "Solicitar rol organizador" }));
    expect(screen.getByRole("status").textContent).toContain("Solicitando rol");
    expect(screen.getByRole("button", { name: "Solicitar rol organizador" }).hasAttribute("disabled")).toBe(true);
    await act(async () => { finish({ ok: true, json: async () => ({ roles: [{ role: "cliente", status: "activo" }, { role: "organizador", status: "pendiente" }] }) }); });
    expect(await screen.findByText("organizador: pendiente")).toBeTruthy();
  });
  it.each(["pendiente", "deshabilitado"])("shows organizer %s independently of the client role", async (status) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ account_id: "123", email: "user@example.com", roles: [{ role: "cliente", status: "activo" }, { role: "organizador", status }] }) }));
    render(<AccountView token="token" onInvalidSession={vi.fn()} />);
    expect((await screen.findByText(`organizador: ${status}`)).textContent).toContain(status);
    expect(screen.getByText("cliente: activo")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Solicitar rol/ })).toBeNull();
  });

  it("requests a missing role and displays the returned roles", async () => {
    const roles = [{ role: "cliente", status: "activo" }, { role: "organizador", status: "pendiente" }];
    const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => ({ account_id: "123", email: "user@example.com", roles: roles.slice(0, 1) }) }).mockResolvedValueOnce({ ok: true, json: async () => ({ roles }) });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<AccountView token="token" onInvalidSession={vi.fn()} />);
    await user.click(await screen.findByRole("button", { name: "Solicitar rol organizador" }));
    expect((await screen.findByText("organizador: pendiente")).textContent).toContain("pendiente");
    expect(screen.getByText("cliente: activo")).toBeTruthy();
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ role: "organizador" });
    expect(screen.queryByRole("button", { name: "Solicitar rol organizador" })).toBeNull();
  });

  it("reports a duplicate role without changing the account", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({ ok: true, json: async () => ({ account_id: "123", email: "user@example.com", roles: [{ role: "cliente", status: "activo" }] }) }).mockResolvedValueOnce({ ok: false, status: 409 }));
    const user = userEvent.setup();
    render(<AccountView token="token" onInvalidSession={vi.fn()} />);
    await user.click(await screen.findByRole("button", { name: "Solicitar rol organizador" }));
    expect((await screen.findByRole("alert")).textContent).toContain("ya está asignado");
    expect(screen.getByText("cliente: activo")).toBeTruthy();
    expect(screen.queryByText("organizador: pendiente")).toBeNull();
  });

  it("invalidates an unauthorized session without displaying account data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401 }));
    const invalid = vi.fn();
    render(<AccountView token="invalid" onInvalidSession={invalid} />);
    await vi.waitFor(() => expect(invalid).toHaveBeenCalledOnce());
    expect(screen.queryByText(/Email:/)).toBeNull();
  });

  it("hides previous roles while refreshing the account and after a failed request", async () => {
    let failRequest!: (reason: Error) => void;
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ account_id: "123", email: "user@example.com", roles: [{ role: "organizador", status: "habilitado" }] }) })
      .mockImplementationOnce(() => new Promise((_resolve, reject) => { failRequest = reject; }));
    vi.stubGlobal("fetch", fetchMock);
    const invalid = vi.fn();
    const { rerender } = render(<AccountView token="first-token" onInvalidSession={invalid} />);
    expect(await screen.findByText("organizador: habilitado")).toBeTruthy();
    rerender(<AccountView token="renewed-token" onInvalidSession={invalid} />);
    expect(screen.queryByText("organizador: habilitado")).toBeNull();
    expect(screen.getByRole("status").textContent).toContain("Cargando");
    failRequest(new Error("offline"));
    expect((await screen.findByRole("alert")).textContent).toContain("No se pudo consultar");
    expect(screen.queryByText("organizador: habilitado")).toBeNull();
    expect(screen.queryByText(/Email:/)).toBeNull();
  });

  it("ignores a late 401 from a role request made with the previous token", async () => {
    let finishRole!: (response: { ok: boolean; status: number }) => void;
    const account = { account_id: "123", email: "user@example.com", roles: [{ role: "cliente", status: "activo" }] };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => account })
      .mockImplementationOnce(() => new Promise((resolve) => { finishRole = resolve; }))
      .mockResolvedValueOnce({ ok: true, json: async () => account });
    vi.stubGlobal("fetch", fetchMock);
    const invalid = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(<AccountView token="first-token" onInvalidSession={invalid} />);
    await user.click(await screen.findByRole("button", { name: "Solicitar rol organizador" }));
    rerender(<AccountView token="renewed-token" onInvalidSession={invalid} />);
    expect(await screen.findByText("cliente: activo")).toBeTruthy();
    await act(async () => { finishRole({ ok: false, status: 401 }); });
    expect(invalid).not.toHaveBeenCalled();
    expect(screen.getByText("cliente: activo")).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it.each([false, true])("reconciles a late successful role request after token renewal (account changed: %s)", async (accountChanged) => {
    let finishRole!: (response: { ok: boolean; json: () => Promise<object> }) => void;
    const firstAccount = { account_id: "123", email: "first@example.com", roles: [{ role: "cliente", status: "activo" }] };
    const currentAccount = accountChanged ? { ...firstAccount, account_id: "456", email: "second@example.com" } : firstAccount;
    const refreshedAccount = accountChanged ? currentAccount : { ...currentAccount, roles: [...currentAccount.roles, { role: "organizador", status: "pendiente" }] };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => firstAccount })
      .mockImplementationOnce(() => new Promise((resolve) => { finishRole = resolve; }))
      .mockResolvedValueOnce({ ok: true, json: async () => currentAccount })
      .mockResolvedValueOnce({ ok: true, json: async () => refreshedAccount });
    vi.stubGlobal("fetch", fetchMock);
    const invalid = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(<AccountView token="first-token" onInvalidSession={invalid} />);
    await user.click(await screen.findByRole("button", { name: "Solicitar rol organizador" }));
    rerender(<AccountView token="renewed-token" onInvalidSession={invalid} />);
    expect(await screen.findByText(`Email: ${currentAccount.email}`)).toBeTruthy();
    await act(async () => { finishRole({ ok: true, json: async () => ({ roles: [{ role: "organizador", status: "pendiente" }] }) }); });
    expect(await screen.findByText(`Email: ${refreshedAccount.email}`)).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(4);
    expect(fetchMock.mock.calls[3][1].headers.Authorization).toBe("Bearer renewed-token");
    expect(Boolean(screen.queryByText("organizador: pendiente"))).toBe(!accountChanged);
    if (accountChanged) expect(screen.queryByText("Email: first@example.com")).toBeNull();
    expect(invalid).not.toHaveBeenCalled();
  });
});
