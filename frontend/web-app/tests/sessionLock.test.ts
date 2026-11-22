import { afterEach, describe, expect, it, vi } from "vitest";
import { SessionCoordinationUnavailable, withSessionLock } from "../src/sessionLock";

afterEach(() => vi.unstubAllGlobals());

describe("session coordination", () => {
  it("does not start an operation when Web Locks are unavailable", async () => {
    vi.stubGlobal("navigator", {});
    const operation = vi.fn();
    await expect(withSessionLock(operation)).rejects.toBeInstanceOf(SessionCoordinationUnavailable);
    expect(operation).not.toHaveBeenCalled();
  });

  it("holds the shared lock until the first operation completes", async () => {
    let queue = Promise.resolve();
    const request = vi.fn((_name: string, _options: object, callback: () => Promise<void>) => {
      const result = queue.then(callback);
      queue = result;
      return result;
    });
    vi.stubGlobal("navigator", { locks: { request } });
    let release!: () => void;
    const firstStarted = vi.fn();
    const secondStarted = vi.fn();
    const first = withSessionLock(async () => {
      firstStarted();
      await new Promise<void>((resolve) => { release = resolve; });
    });
    const second = withSessionLock(async () => { secondStarted(); });
    await vi.waitFor(() => expect(firstStarted).toHaveBeenCalledOnce());
    expect(secondStarted).not.toHaveBeenCalled();
    release();
    await Promise.all([first, second]);
    expect(secondStarted).toHaveBeenCalledOnce();
    expect(request).toHaveBeenCalledTimes(2);
    expect(request.mock.calls[0][0]).toBe(request.mock.calls[1][0]);
    expect(request.mock.calls[0][1]).toEqual({ mode: "exclusive" });
  });
});
