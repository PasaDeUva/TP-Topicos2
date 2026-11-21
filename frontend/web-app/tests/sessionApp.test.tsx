import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../src/App";

const mocks = vi.hoisted(() => ({ restore: vi.fn(), signOut: vi.fn(), change: undefined as (() => void) | undefined }));
vi.mock("../src/sessionCoordinator", () => ({
  SessionCoordinator: class {
    constructor(onChange: () => void) { mocks.change = onChange; }
    restore = mocks.restore;
    signOut = mocks.signOut;
    close() { /* No shared resources in this test. */ }
  },
}));

beforeEach(() => {
  mocks.restore.mockResolvedValue({ access_token: "access-secret", csrf_token: "csrf-secret", expires_in: 600, generation: "one" });
  mocks.signOut.mockResolvedValue(undefined);
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ account_id: "123", email: "user@example.com", roles: [] }) }));
});
afterEach(() => { cleanup(); vi.clearAllMocks(); vi.unstubAllGlobals(); });

describe("session interface", () => {
  it("returns to login when Identity rejects an earlier access token", async () => {
    mocks.restore.mockResolvedValueOnce({ access_token: "legacy-access", csrf_token: "csrf-secret", expires_in: 600, generation: "one" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401 }));
    render(<App />);
    expect(await screen.findByText("La sesión no es válida. Inicie sesión nuevamente.")).toBeTruthy();
    expect(screen.queryByText(/Email:/)).toBeNull();
  });
  it("restores a session and clears account data after logout", async () => {
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByText("Email: user@example.com")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));
    expect(await screen.findByText("Sesión cerrada.")).toBeTruthy();
    expect(mocks.signOut).toHaveBeenCalledWith("one");
    expect(screen.queryByText("Email: user@example.com")).toBeNull();
    expect(JSON.stringify(localStorage)).not.toContain("access-secret");
  });

  it("hides the account when another tab invalidates the session", async () => {
    render(<App />);
    expect(await screen.findByText("Email: user@example.com")).toBeTruthy();
    mocks.change?.();
    expect(await screen.findByText("La sesión no es válida. Inicie sesión nuevamente.")).toBeTruthy();
    expect(screen.queryByText("Email: user@example.com")).toBeNull();
  });

  it("clears a session at expiry instead of repeatedly renewing a nearly expired token", async () => {
    mocks.restore.mockResolvedValueOnce({ access_token: "short-lived", csrf_token: "csrf-secret", expires_in: 0.2, generation: "one" });
    render(<App />);
    expect(await screen.findByText("Email: user@example.com")).toBeTruthy();
    expect(await screen.findByText("La sesión no es válida. Inicie sesión nuevamente.")).toBeTruthy();
    expect(screen.queryByText("Email: user@example.com")).toBeNull();
    expect(mocks.restore).toHaveBeenCalledTimes(1);
  });

  it("hides the account when an in-flight refresh exceeds expiry", async () => {
    vi.useFakeTimers();
    mocks.restore.mockResolvedValueOnce({ access_token: "access", csrf_token: "csrf", expires_in: 31, generation: "one" });
    mocks.restore.mockImplementationOnce(() => new Promise(() => {}));
    render(<App />);
    await act(async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(mocks.restore).toHaveBeenCalledTimes(2);
    await act(async () => { await vi.advanceTimersByTimeAsync(30000); });
    expect(screen.queryByText("Email: user@example.com")).toBeNull();
    expect(screen.getByText("La sesión no es válida. Inicie sesión nuevamente.")).toBeTruthy();
    vi.useRealTimers();
  });
});
