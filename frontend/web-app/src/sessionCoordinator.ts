import { IdentityError, login, logoutSession, readCsrf, refreshSession, type WebSession } from "./identity";
import { SessionCoordinationUnavailable, withSessionLock } from "./sessionLock";

const STATE_KEY = "tp-topicos2-session-state";
const LOGOUT_KEY = "tp-topicos2-session-logout";
const CHANNEL = "tp-topicos2-session-events";
type SharedState = { generation: string; uncertain: boolean };
export type CoordinatedSession = WebSession & { generation: string };

export class SessionCoordinator {
  private channel: BroadcastChannel;

  constructor(onChange: () => void) {
    if (typeof BroadcastChannel === "undefined" || !navigator.locks) throw new SessionCoordinationUnavailable();
    this.channel = new BroadcastChannel(CHANNEL);
    this.channel.onmessage = () => onChange();
  }

  close() { this.channel.close(); }

  private read(): SharedState | null {
    const value = localStorage.getItem(STATE_KEY);
    if (value === null) return null;
    const parsed: unknown = JSON.parse(value);
    if (!parsed || typeof parsed !== "object" || !("generation" in parsed) || typeof parsed.generation !== "string" || !("uncertain" in parsed) || typeof parsed.uncertain !== "boolean") throw new SessionCoordinationUnavailable();
    return parsed as SharedState;
  }

  private write(state: SharedState) { localStorage.setItem(STATE_KEY, JSON.stringify(state)); }

  async signIn(email: string, password: string): Promise<CoordinatedSession> {
    return withSessionLock(async () => {
      const previous = this.read();
      const state = { generation: crypto.randomUUID(), uncertain: true };
      this.write(state);
      let session: WebSession;
      try {
        session = await login(email, password);
      } catch (error) {
        if (error instanceof IdentityError && (error.status === 400 || error.status === 401)) {
          if (previous) this.write(previous);
          else localStorage.removeItem(STATE_KEY);
        } else {
          this.channel.postMessage("invalidate");
        }
        throw error;
      }
      this.write({ ...state, uncertain: false });
      localStorage.removeItem(LOGOUT_KEY);
      this.channel.postMessage("invalidate");
      return { ...session, generation: state.generation };
    });
  }

  async restore(expectedGeneration?: string): Promise<CoordinatedSession> {
    return withSessionLock(async () => {
      const existing = this.read();
      if (existing?.uncertain || (expectedGeneration && existing?.generation !== expectedGeneration)) throw new SessionCoordinationUnavailable();
      const state = existing ?? { generation: crypto.randomUUID(), uncertain: false };
      if (localStorage.getItem(LOGOUT_KEY) === state.generation) throw new SessionCoordinationUnavailable();
      const csrf = await readCsrf();
      if (localStorage.getItem(LOGOUT_KEY) === state.generation) throw new SessionCoordinationUnavailable();
      this.write({ ...state, uncertain: true });
      try {
        const session = await refreshSession(csrf);
        if (localStorage.getItem(LOGOUT_KEY) === state.generation) throw new SessionCoordinationUnavailable();
        this.write(state);
        return { ...session, generation: state.generation };
      } catch (error) {
        this.channel.postMessage("invalidate");
        throw error;
      }
    });
  }

  async signOut(generation: string): Promise<void> {
    const current = this.read();
    if (!current || current.generation !== generation) throw new SessionCoordinationUnavailable();
    localStorage.setItem(LOGOUT_KEY, generation);
    this.channel.postMessage("invalidate");
    return withSessionLock(async () => {
      const state = this.read();
      if (!state || state.generation !== generation || localStorage.getItem(LOGOUT_KEY) !== generation) throw new SessionCoordinationUnavailable();
      this.write({ ...state, uncertain: true });
      const csrf = await readCsrf();
      await logoutSession(csrf);
    });
  }
}
