import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import OrganizerAdmin from "../src/OrganizerAdmin";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("lists organizers and applies a confirmed change", async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [{ account_id: "123", email: "org@example.com", status: "pendiente" }] }).mockResolvedValueOnce({ ok: true, json: async () => ({ account_id: "123", status: "habilitado" }) });
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<OrganizerAdmin token="token" onInvalidSession={vi.fn()} />);
  await user.click(await screen.findByRole("button", { name: "Habilitar org@example.com" }));
  expect(await screen.findByText("habilitado")).toBeTruthy();
});

it("shows all organizer states and disables an enabled organizer", async () => {
  const items = [{ account_id: "1", email: "one@example.com", status: "pendiente" }, { account_id: "2", email: "two@example.com", status: "habilitado" }, { account_id: "3", email: "three@example.com", status: "deshabilitado" }];
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({ ok: true, json: async () => items }).mockResolvedValueOnce({ ok: true, json: async () => ({ account_id: "2", status: "deshabilitado" }) }));
  const user = userEvent.setup();
  render(<OrganizerAdmin token="token" onInvalidSession={vi.fn()} />);
  expect(await screen.findByText("pendiente")).toBeTruthy();
  expect(screen.getByText("habilitado")).toBeTruthy();
  expect(screen.getByText("deshabilitado")).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Deshabilitar two@example.com" }));
  expect(await screen.findByRole("button", { name: "Habilitar two@example.com" })).toBeTruthy();
});

it("hides stale data and ignores old requests on token change", async () => {
  let finish!: (value: object) => void;
  vi.stubGlobal("fetch", vi.fn().mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; })).mockResolvedValueOnce({ ok: true, json: async () => [] }));
  const { rerender } = render(<OrganizerAdmin token="old" onInvalidSession={vi.fn()} />);
  rerender(<OrganizerAdmin token="new" onInvalidSession={vi.fn()} />);
  expect(await screen.findByText(/No hay organizadores/)).toBeTruthy();
  await act(async () => { finish({ ok: true, json: async () => [{ account_id: "old", email: "old@example.com", status: "pendiente" }] }); });
  expect(screen.queryByText("old@example.com")).toBeNull();
});

it("does not reveal data when access is forbidden", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 403 }));
  render(<OrganizerAdmin token="token" onInvalidSession={vi.fn()} />);
  expect((await screen.findByRole("alert")).textContent).toContain("permisos");
});

it("allows the organizer action to be reached and activated by keyboard", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [{ account_id: "123", email: "org@example.com", status: "pendiente" }] }).mockResolvedValueOnce({ ok: true, json: async () => ({ account_id: "123", status: "habilitado" }) }));
  const user = userEvent.setup();
  render(<OrganizerAdmin token="token" onInvalidSession={vi.fn()} />);
  const button = await screen.findByRole("button", { name: "Habilitar org@example.com" });
  await user.tab();
  expect(document.activeElement).toBe(button);
  await user.keyboard("{Enter}");
  expect(await screen.findByText("habilitado")).toBeTruthy();
});

it("invalidates a session rejected by Identity", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401 }));
  const invalid = vi.fn();
  render(<OrganizerAdmin token="token" onInvalidSession={invalid} />);
  await vi.waitFor(() => expect(invalid).toHaveBeenCalledOnce());
});

it("retries an unsuccessful list request", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ ok: true, json: async () => [] }));
  const user = userEvent.setup();
  render(<OrganizerAdmin token="token" onInvalidSession={vi.fn()} />);
  await user.click(await screen.findByRole("button", { name: "Reintentar" }));
  expect(await screen.findByText(/No hay organizadores/)).toBeTruthy();
});

it("hides administrative data if mutation returns forbidden", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [{ account_id: "123", email: "org@example.com", status: "pendiente" }] }).mockResolvedValueOnce({ ok: false, status: 403 }));
  const user = userEvent.setup();
  render(<OrganizerAdmin token="token" onInvalidSession={vi.fn()} />);
  await user.click(await screen.findByRole("button", { name: "Habilitar org@example.com" }));
  expect((await screen.findByRole("alert")).textContent).toContain("permisos");
  expect(screen.queryByText("org@example.com")).toBeNull();
});

it("reconciles an uncertain mutation only after a fresh query", async () => {
  let finish!: (reason: Error) => void;
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [{ account_id: "123", email: "org@example.com", status: "pendiente" }] }).mockImplementationOnce(() => new Promise((_resolve, reject) => { finish = reject; })).mockResolvedValueOnce({ ok: true, json: async () => [{ account_id: "123", email: "org@example.com", status: "habilitado" }] });
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<OrganizerAdmin token="token" onInvalidSession={vi.fn()} />);
  await user.click(await screen.findByRole("button", { name: "Habilitar org@example.com" }));
  expect(screen.getByRole("status").textContent).toContain("Actualizando");
  await act(async () => { finish(new Error("lost response")); });
  expect(await screen.findByText("habilitado")).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledTimes(3);
});
