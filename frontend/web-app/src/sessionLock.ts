const SESSION_LOCK = "tp-topicos2-web-session";

export class SessionCoordinationUnavailable extends Error {
  constructor() {
    super("Session coordination is unavailable");
  }
}

/** Serializes all operations that can rotate or revoke the shared cookie. */
export async function withSessionLock<T>(operation: () => Promise<T>): Promise<T> {
  if (!navigator.locks || typeof navigator.locks.request !== "function") {
    throw new SessionCoordinationUnavailable();
  }
  return navigator.locks.request(SESSION_LOCK, { mode: "exclusive" }, operation);
}
