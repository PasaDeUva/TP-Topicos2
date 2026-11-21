import { useEffect, useRef, useState } from "react";
import { getAccount, IdentityError, requestRole, type Account, type Role } from "./identity";
import OrganizerAdmin from "./OrganizerAdmin";

type Props = { token: string; onInvalidSession: () => void };

export default function AccountView({ token, onInvalidSession }: Props) {
  const [revision, setRevision] = useState(0);
  const [snapshot, setSnapshot] = useState<{ token: string; revision: number; account: Account } | null>(null);
  const [failure, setFailure] = useState<{ token: string; revision: number; message: string } | null>(null);
  const [busyToken, setBusyToken] = useState<string | null>(null);
  const activeRequestScope = useRef<AbortController | null>(null);
  const mounted = useRef(false);
  const account = snapshot?.token === token && snapshot.revision === revision ? snapshot.account : null;
  const error = failure?.token === token && failure.revision === revision ? failure.message : "";
  const busy = busyToken === token;

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    activeRequestScope.current = controller;
    getAccount(token, controller.signal).then((result) => {
      if (!controller.signal.aborted) setSnapshot({ token, revision, account: result });
    }).catch((cause: unknown) => {
      if (controller.signal.aborted) return;
      if (cause instanceof IdentityError && cause.status === 401) onInvalidSession();
      else {
        setSnapshot(null);
        setFailure({ token, revision, message: "No se pudo consultar la cuenta. Intente nuevamente." });
      }
    });
    return () => {
      controller.abort();
      if (activeRequestScope.current === controller) activeRequestScope.current = null;
    };
  }, [token, revision, onInvalidSession]);

  async function addRole(role: Role) {
    const scope = activeRequestScope.current;
    if (!scope || scope.signal.aborted) return;
    setBusyToken(token);
    setFailure(null);
    try {
      const roles = await requestRole(token, role);
      if (scope.signal.aborted) {
        if (mounted.current) setRevision((current) => current + 1);
        return;
      }
      setSnapshot((current) => current?.token === token ? { ...current, account: { ...current.account, roles } } : current);
    } catch (cause) {
      if (scope.signal.aborted) {
        if (mounted.current && cause instanceof IdentityError && cause.status === 409) setRevision((current) => current + 1);
        return;
      }
      if (cause instanceof IdentityError && cause.status === 401) onInvalidSession();
      else if (cause instanceof IdentityError && cause.status === 409) setFailure({ token, revision, message: "El rol ya está asignado a la cuenta." });
      else setFailure({ token, revision, message: "No se pudo solicitar el rol. Intente nuevamente." });
    } finally {
      setBusyToken((current) => current === token ? null : current);
    }
  }

  return <section>
    <div className="panel-heading"><h2>Mi cuenta</h2><p>Consultá los datos y roles asociados a tu cuenta.</p></div>
    {error && <p className="notice notice-error" role="alert">{error}</p>}
    {!account && !error && <p className="state" role="status">Cargando cuenta...</p>}
    {account && <>
      <div className="account-details"><p>Email: {account.email}</p><p>Identificador: {account.account_id}</p></div>
      <div className="section-heading"><h3>Roles</h3><p>Permisos asociados a tu cuenta.</p></div>
      {account.roles.length === 0 ? <p className="empty-state">No hay roles asociados a tu cuenta.</p> : <ul className="role-list">{account.roles.map((item) => <li key={item.role}><span className="badge">{item.role}: {item.status}</span></li>)}</ul>}
      {!account.roles.some((item) => item.role === "organizador") && <p className="role-hint">El rol de organizador requiere habilitación después de solicitarlo.</p>}
      {busy && <p className="role-progress" role="status">Solicitando rol...</p>}
      <div className="role-actions">
      {(["cliente", "organizador"] as const).filter((role) => !account.roles.some((item) => item.role === role)).map((role) =>
        <button className="button button-secondary" key={role} disabled={busy} onClick={() => void addRole(role)}>Solicitar rol {role}</button>,
      )}
      </div>
      {account.roles.some((item) => item.role === "administrador" && item.status === "activo") && <OrganizerAdmin token={token} onInvalidSession={onInvalidSession} />}
    </>}
  </section>;
}
