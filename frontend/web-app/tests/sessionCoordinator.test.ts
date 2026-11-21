import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SessionCoordinator } from "../src/sessionCoordinator";
import { IdentityError, login, logoutSession, readCsrf, refreshSession } from "../src/identity";

vi.mock("../src/identity", async (importOriginal) => ({ ...await importOriginal<typeof import("../src/identity")>(), login: vi.fn(), logoutSession: vi.fn(), readCsrf: vi.fn(), refreshSession: vi.fn() }));

class FakeChannel {
  static channels: FakeChannel[] = [];
  onmessage: (() => void) | null = null;
  constructor() { FakeChannel.channels.push(this); }
  postMessage() { FakeChannel.channels.filter((channel) => channel !== this).forEach((channel) => channel.onmessage?.()); }
  close() { FakeChannel.channels = FakeChannel.channels.filter((channel) => channel !== this); }
}

beforeEach(() => {
  localStorage.clear();
  FakeChannel.channels = [];
  let queue = Promise.resolve<unknown>(undefined);
  vi.stubGlobal("BroadcastChannel", FakeChannel);
  vi.stubGlobal("navigator", { locks: { request: (_name: string, _options: object, callback: () => Promise<unknown>) => {
    const result = queue.then(callback);
    queue = result.catch(() => undefined);
    return result;
  } } });
  vi.mocked(readCsrf).mockResolvedValue("csrf-secret");
  vi.mocked(login).mockResolvedValue({ access_token: "access-secret", csrf_token: "csrf-secret", expires_in: 600 });
  vi.mocked(refreshSession).mockResolvedValue({ access_token: "new-secret", csrf_token: "csrf-secret", expires_in: 600 });
  vi.mocked(logoutSession).mockResolvedValue(undefined);
});

afterEach(() => { vi.clearAllMocks(); vi.unstubAllGlobals(); });

describe("session coordinator", () => {
  it("serializes concurrent renewals and does not persist tokens", async () => {
    const first = new SessionCoordinator(vi.fn());
    const second = new SessionCoordinator(vi.fn());
    const session = await first.signIn("user@example.com", "password");
    await Promise.all([first.restore(session.generation), second.restore(session.generation)]);
    expect(readCsrf).toHaveBeenCalledTimes(2);
    expect(refreshSession).toHaveBeenCalledTimes(2);
    expect(JSON.stringify(localStorage)).not.toContain("secret");
    first.close(); second.close();
  });

  it("blocks further renewal after a lost response until a new login", async () => {
    const onRemoteChange = vi.fn();
    const first = new SessionCoordinator(vi.fn());
    const second = new SessionCoordinator(onRemoteChange);
    const session = await first.signIn("user@example.com", "password");
    vi.mocked(refreshSession).mockRejectedValueOnce(new Error("network failure"));
    await expect(first.restore(session.generation)).rejects.toThrow("network failure");
    await expect(second.restore(session.generation)).rejects.toThrow();
    expect(refreshSession).toHaveBeenCalledTimes(1);
    expect(onRemoteChange).toHaveBeenCalledTimes(2);
    await first.signIn("user@example.com", "password");
    await expect(first.restore()).resolves.toMatchObject({ access_token: "new-secret" });
    first.close(); second.close();
  });

  it("notifies other tabs of logout and prevents subsequent renewal", async () => {
    const remote = vi.fn();
    const first = new SessionCoordinator(vi.fn());
    const second = new SessionCoordinator(remote);
    const session = await first.signIn("user@example.com", "password");
    await first.signOut(session.generation);
    expect(logoutSession).toHaveBeenCalledWith("csrf-secret");
    expect(remote).toHaveBeenCalledTimes(2);
    await expect(second.restore(session.generation)).rejects.toThrow();
    expect(refreshSession).not.toHaveBeenCalled();
    first.close(); second.close();
  });

  it.each([400, 401])("keeps the existing session usable when another tab's login returns %i", async (status) => {
    const remote = vi.fn();
    const first = new SessionCoordinator(remote);
    const second = new SessionCoordinator(vi.fn());
    const session = await first.signIn("user@example.com", "password");
    remote.mockClear();
    vi.mocked(login).mockRejectedValueOnce(new IdentityError(status));
    await expect(second.signIn("user@example.com", "wrong")).rejects.toMatchObject({ status });
    expect(remote).not.toHaveBeenCalled();
    await expect(first.restore(session.generation)).resolves.toMatchObject({ generation: session.generation });
    first.close(); second.close();
  });

  it("invalidates other tabs before a logout CSRF request that fails", async () => {
    const remote = vi.fn();
    const first = new SessionCoordinator(vi.fn());
    const second = new SessionCoordinator(remote);
    const session = await first.signIn("user@example.com", "password");
    remote.mockClear();
    vi.mocked(readCsrf).mockRejectedValueOnce(new Error("offline"));
    await expect(first.signOut(session.generation)).rejects.toThrow("offline");
    expect(remote).toHaveBeenCalledOnce();
    await expect(second.restore(session.generation)).rejects.toThrow();
    expect(refreshSession).not.toHaveBeenCalled();
    first.close(); second.close();
  });

  it("notifies other tabs even while the logout CSRF request is pending", async () => {
    const remote = vi.fn();
    const first = new SessionCoordinator(vi.fn());
    const second = new SessionCoordinator(remote);
    const session = await first.signIn("user@example.com", "password");
    remote.mockClear();
    let resolveCsrf!: (value: string) => void;
    vi.mocked(readCsrf).mockImplementationOnce(() => new Promise((resolve) => { resolveCsrf = resolve; }));
    const closing = first.signOut(session.generation);
    await vi.waitFor(() => expect(remote).toHaveBeenCalledOnce());
    expect(logoutSession).not.toHaveBeenCalled();
    resolveCsrf("csrf-secret");
    await closing;
    first.close(); second.close();
  });

  it("propagates logout while another tab holds the lock for a pending refresh", async () => {
    const remote = vi.fn();
    const first = new SessionCoordinator(remote);
    const second = new SessionCoordinator(vi.fn());
    const session = await first.signIn("user@example.com", "password");
    let finishRefresh!: (value: { access_token: string; csrf_token: string; expires_in: number }) => void;
    vi.mocked(refreshSession).mockImplementationOnce(() => new Promise((resolve) => { finishRefresh = resolve; }));
    const refresh = first.restore(session.generation);
    const refreshResult = expect(refresh).rejects.toThrow();
    await vi.waitFor(() => expect(refreshSession).toHaveBeenCalledOnce());
    const closing = second.signOut(session.generation);
    expect(remote).toHaveBeenCalledOnce();
    expect(logoutSession).not.toHaveBeenCalled();
    finishRefresh({ access_token: "new-secret", csrf_token: "csrf-secret", expires_in: 600 });
    await refreshResult;
    await closing;
    expect(logoutSession).toHaveBeenCalledWith("csrf-secret");
    await expect(first.restore(session.generation)).rejects.toThrow();
    expect(refreshSession).toHaveBeenCalledOnce();
    first.close(); second.close();
  });
});
