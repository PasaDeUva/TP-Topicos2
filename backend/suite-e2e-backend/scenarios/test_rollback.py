"""Escenario multiservicio: Verificación de compatibilidad con versiones previas (Rollback).

Servicios involucrados:
- events-service: Catálogo y endpoints de eventos.
- compras-service: Endpoints de compras.

Escenarios que valida este test:
1. Validación Condicional de Rollback:
   - Si no se especifica el parámetro '--rollback-ref', el test finaliza inmediatamente sin acción.
   - Si se especifica una referencia Git válida (ej. commit previo a la integración de identidad):
     a. Verifica que en la versión actual las escrituras anónimas (sin token) son rechazadas con 401 Unauthorized.
     b. Carga y sobrescribe los routers y schemas con las fuentes de la revisión histórica indicada.
     c. Reinicia los servicios y valida que la versión anterior permita escrituras anónimas con compatibilidad
        de formato (ej. especificando 'owner_id' o 'cliente_id' explícitamente en el cuerpo).
"""

import subprocess
from pathlib import Path

from harness.client import wait_ready
from harness.context import E2EContext


def load_rollback_files(source_root: Path, ref: str) -> dict[str, bytes]:
    if ref.startswith("-"):
        raise ValueError("Invalid rollback revision")
    files = {}
    for service in ("events-service", "compras-service"):
        for filename in ("routers.py", "schemas.py"):
            path = f"backend/{service}/app/{filename}"
            try:
                result = subprocess.run(
                    ["git", "show", f"{ref}:{path}"],
                    cwd=source_root,
                    check=True,
                    capture_output=True,
                )
            except (OSError, subprocess.CalledProcessError):
                raise ValueError("Rollback revision or required files are unavailable locally") from None
            files[path] = result.stdout
    return files


def run(ctx: E2EContext):
    """Verify rollback permits anonymous writes if rollback_ref is provided."""
    if not ctx.rollback_ref:
        return

    ctx.ensure_purchase()
    source_root = Path(__file__).resolve().parents[3]
    rollback_files = load_rollback_files(source_root, ctx.rollback_ref)
    event_payload = ctx.state["event_payload"]
    body = ctx.state["purchase_body"]
    key = ctx.state["purchase_key"]
    customer_id = ctx.state["customer_id"]
    organizer_id = ctx.state["organizer_id"]

    # Anonymous writes fail on modern revision
    ctx.request("events", "POST", "/eventos", event_payload, expected=401)
    ctx.request("purchases", "POST", "/compras", body, headers=key, expected=401)

    for path, source in rollback_files.items():
        (ctx.root / path).write_bytes(source)

    ctx.compose("restart", "events-service", "compras-service")
    ctx.refresh_urls()
    wait_ready(ctx.events_url, "/eventos")
    wait_ready(ctx.purchases_url, f"/compras?cliente_id={customer_id}")

    old_event = ctx.request(
        "events",
        "POST",
        "/eventos",
        {**event_payload, "owner_id": organizer_id},
        expected=201,
    )
    old_body = {
        "cliente_id": customer_id,
        "evento_id": old_event["id"],
        "modalidad_id": old_event["modalidades"][0]["id"],
    }
    ctx.request(
        "purchases",
        "POST",
        "/compras",
        old_body,
        headers={"Idempotency-Key": "rollback-key"},
        expected=201,
    )
