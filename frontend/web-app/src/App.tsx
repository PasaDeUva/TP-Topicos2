import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import AccountView from "./AccountView";
import { IdentityError, register, type Role } from "./identity";
import { SessionCoordinator, type CoordinatedSession } from "./sessionCoordinator";

export default function App() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("cliente");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [session, setSession] = useState<CoordinatedSession | null>(null);
  const [restoring, setRestoring] = useState(true);
  const coordinator = useRef<SessionCoordinator | null>(null);
  const revision = useRef(0);
  const invalidateSession = useCallback(() => {
    revision.current += 1;
    setSession(null);
    setMessage("");
    setError("La sesión no es válida. Inicie sesión nuevamente.");
  }, []);

  useEffect(() => {
    let active = true;
    let instance: SessionCoordinator | undefined;
    const currentRevision = revision.current;
    Promise.resolve().then(() => {
      if (!active) return null;
      instance = new SessionCoordinator(invalidateSession);
      coordinator.current = instance;
      return instance.restore();
    }).then((result) => {
      if (result && active && revision.current === currentRevision) setSession(result);
    }).catch((cause: unknown) => {
      if (active && !(cause instanceof IdentityError && cause.status === 401)) {
        setError("No se pudo restaurar la sesión. Inicie sesión nuevamente.");
      }
    }).finally(() => { if (active) setRestoring(false); });
    return () => {
      active = false;
      coordinator.current = null;
      instance?.close();
    };
  }, [invalidateSession]);

  useEffect(() => {
    if (!session) return;
    const currentRevision = revision.current;
    const expiryTimer = window.setTimeout(invalidateSession, Math.max(0, session.expires_in * 1000));
    if (session.expires_in <= 30) return () => window.clearTimeout(expiryTimer);
    const timer = window.setTimeout(() => {
      coordinator.current?.restore(session.generation).then((result) => {
        if (revision.current === currentRevision) setSession(result);
      }).catch(() => {
        if (revision.current === currentRevision) invalidateSession();
      });
    }, Math.max(0, session.expires_in * 1000 - 30000));
    return () => { window.clearTimeout(timer); window.clearTimeout(expiryTimer); };
  }, [session, invalidateSession]);

  async function signOut() {
    if (!session || !coordinator.current) return;
    const current = session;
    revision.current += 1;
    setSession(null);
    setEmail("");
    setPassword("");
    setBusy(true);
    try {
      await coordinator.current.signOut(current.generation);
      setMessage("Sesión cerrada.");
    } catch {
      setError("No se pudo confirmar el cierre. Inicie sesión nuevamente.");
    } finally {
      setBusy(false);
    }
  }

  function changeMode(next: "login" | "register") {
    setMode(next);
    setPassword("");
    setError("");
    setMessage("");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (!email.trim() || !email.includes("@") || !password || (mode === "register" && password.length < 8)) {
      setError(mode === "register" ? "Ingrese un email válido y una contraseña de al menos 8 caracteres." : "Ingrese un email válido y su contraseña.");
      return;
    }
    setBusy(true);
    try {
      if (mode === "register") {
        await register(email, password, role);
        setPassword("");
        setMode("login");
        setMessage(role === "organizador" ? "Cuenta creada. El rol organizador está pendiente de habilitación. Inicie sesión para continuar." : "Cuenta creada. Inicie sesión para continuar.");
      } else {
        if (!coordinator.current) throw new Error("Session coordination unavailable");
        const currentRevision = revision.current;
        const result = await coordinator.current.signIn(email, password);
        setPassword("");
        if (revision.current === currentRevision) setSession(result);
      }
    } catch (cause) {
      if (cause instanceof IdentityError && cause.status === 409 && mode === "register") setError("El email ya está registrado.");
      else if (cause instanceof IdentityError && cause.status === 400) setError("Revise los datos ingresados.");
      else if (cause instanceof IdentityError && cause.status === 401 && mode === "login") setError("No se pudo iniciar sesión con esas credenciales.");
      else setError("No se pudo contactar al servicio. Intente nuevamente.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <h1>Acceso y cuenta</h1>
      {restoring ? <p role="status">Restaurando sesión...</p> : session ? <><AccountView token={session.access_token} onInvalidSession={invalidateSession} /><button type="button" disabled={busy} onClick={() => void signOut()}>Cerrar sesión</button></> : <>
        <h2>{mode === "login" ? "Iniciar sesión" : "Crear cuenta"}</h2>
        {message && <p role="status">{message}</p>}
        {error && <p role="alert">{error}</p>}
        <form onSubmit={submit} noValidate>
          <label>Email <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></label>
          <label>Contraseña <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} required /></label>
          {mode === "register" && <label>Tipo de cuenta <select value={role} onChange={(event) => setRole(event.target.value as Role)}><option value="cliente">Cliente</option><option value="organizador">Organizador</option></select></label>}
          <button type="submit" disabled={busy}>{busy ? "Procesando..." : mode === "login" ? "Ingresar" : "Registrarse"}</button>
        </form>
        <button type="button" disabled={busy} onClick={() => changeMode(mode === "login" ? "register" : "login")}>{mode === "login" ? "Crear cuenta" : "Volver al inicio de sesión"}</button>
      </>}
    </main>
  );
}
