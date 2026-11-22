import { useEffect, useRef, useState } from "react";
import { getOrganizers, IdentityError, setOrganizerStatus, type Organizer, type OrganizerStatus } from "./identity";

type Props = { token: string; onInvalidSession: () => void };

export default function OrganizerAdmin({ token, onInvalidSession }: Props) {
  const [revision, setRevision] = useState(0);
  const [snapshot, setSnapshot] = useState<{ token: string; revision: number; items: Organizer[] } | null>(null);
  const [failure, setFailure] = useState<{ token: string; revision: number; message: string; forbidden: boolean } | null>(null);
  const [busyToken, setBusyToken] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ token: string; message: string } | null>(null);
  const scope = useRef<AbortController | null>(null);
  const mounted = useRef(false);
  const items = snapshot?.token === token && snapshot.revision === revision ? snapshot.items : null;
  const error = failure?.token === token && failure.revision === revision ? failure : null;
  const busy = busyToken === token;

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    const controller = new AbortController();
    scope.current = controller;
    getOrganizers(token, controller.signal).then((result) => {
      if (!controller.signal.aborted) setSnapshot({ token, revision, items: result });
    }).catch((cause: unknown) => {
      if (controller.signal.aborted) return;
      if (cause instanceof IdentityError && cause.status === 401) onInvalidSession();
      else setFailure({ token, revision, forbidden: cause instanceof IdentityError && cause.status === 403, message: cause instanceof IdentityError && cause.status === 403 ? "No tenés permisos para administrar organizadores." : "No se pudo cargar la lista de organizadores." });
    });
    return () => { controller.abort(); if (scope.current === controller) scope.current = null; };
  }, [token, revision, onInvalidSession]);

  async function changeStatus(id: string, status: OrganizerStatus) {
    const currentScope = scope.current;
    if (!currentScope || currentScope.signal.aborted) return;
    setBusyToken(token);
    setFailure(null);
    setNotice(null);
    try {
      const result = await setOrganizerStatus(token, id, status);
      if (currentScope.signal.aborted) { if (mounted.current) setRevision((value) => value + 1); return; }
      setSnapshot((current) => current?.token === token ? { ...current, items: current.items.map((item) => item.account_id === result.account_id ? { ...item, status: result.status } : item) } : current);
    } catch (cause) {
      if (currentScope.signal.aborted) { if (mounted.current) setRevision((value) => value + 1); return; }
      if (cause instanceof IdentityError && cause.status === 401) onInvalidSession();
      else if (cause instanceof IdentityError && cause.status === 403) { setSnapshot(null); setFailure({ token, revision, forbidden: true, message: "No tenés permisos para administrar organizadores." }); }
      else { setSnapshot(null); setNotice({ token, message: "No se pudo confirmar el cambio. Se está consultando el estado actual." }); setRevision((value) => value + 1); }
    } finally { setBusyToken((current) => current === token ? null : current); }
  }

  return <section className="admin-section" aria-labelledby="organizers-heading">
    <div className="section-heading"><h3 id="organizers-heading">Administrar organizadores</h3><p>Consultá las solicitudes y gestioná su habilitación.</p></div>
    {notice?.token === token && <p className="notice notice-error" role="status">{notice.message}</p>}
    {error && <div className="notice notice-error" role="alert">{error.message}{!error.forbidden && <button className="button-link" type="button" onClick={() => setRevision((value) => value + 1)}>Reintentar</button>}</div>}
    {!items && !error && <p className="state" role="status">Cargando organizadores...</p>}
    {items && items.length === 0 && <p className="empty-state">No hay organizadores para administrar.</p>}
    {items && items.length > 0 && <ul className="organizer-list">{items.map((item) => <li key={item.account_id}><div><strong>{item.email}</strong><span className="badge">{item.status}</span></div><button className="button button-secondary" type="button" disabled={busy} onClick={() => void changeStatus(item.account_id, item.status === "habilitado" ? "deshabilitado" : "habilitado")}>{item.status === "habilitado" ? "Deshabilitar" : "Habilitar"}<span className="visually-hidden"> {item.email}</span></button></li>)}</ul>}
    {busy && <p className="state" role="status">Actualizando estado...</p>}
  </section>;
}
