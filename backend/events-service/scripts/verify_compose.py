"""Verificación de caja negra de events-service sobre Compose aislado.

Escenarios AISLADOS de events-service: ejercitan solo endpoints y reglas propias
del servicio. Identity interviene únicamente como emisor de tokens (el arnés
registra las cuentas); no se valida ninguna orquestación con compras-service,
eso vive en backend/suite-e2e-backend/.

Escenarios:
1. Catálogo público: listar y consultar eventos sin credenciales; id inexistente 404.
2. Escritura protegida: sin token 401, rol cliente 403, owner_id ajeno 403.
3. Propiedad y baja lógica: otro organizador recibe 404 al editar/borrar; el dueño
   edita (200) y la baja deja el evento con activo=false.
4. Inventario y reservas: disponibilidad inicial = cupo, reserva descuenta,
   idempotencia de reserva, confirmación, liberación y conflictos 409.
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "suite-e2e-backend"))

from harness import E2EContext, run_scenarios  # noqa: E402


def catalogo_publico(ctx: E2EContext):
    event = ctx.ensure_event()
    listado = ctx.request("events", "GET", "/eventos")
    assert any(item["id"] == event["id"] for item in listado)
    detalle = ctx.request("events", "GET", f"/eventos/{event['id']}")
    assert detalle["id"] == event["id"]
    ctx.request("events", "GET", f"/eventos/{uuid.uuid4()}", expected=404)


def escritura_protegida(ctx: E2EContext):
    ctx.ensure_users()
    payload = ctx.build_event_payload()
    organizer = ctx.state["organizer_tokens"]["access_token"]
    customer = ctx.state["customer_tokens"]["access_token"]

    ctx.request("events", "POST", "/eventos", payload, expected=401)
    ctx.request("events", "POST", "/eventos", payload, token=customer, expected=403)
    ajeno = {**payload, "owner_id": ctx.state["other_organizer_id"]}
    ctx.request("events", "POST", "/eventos", ajeno, token=organizer, expected=403)


def propiedad_y_baja_logica(ctx: E2EContext):
    event = ctx.ensure_event()
    payload = ctx.state["event_payload"]
    owner = ctx.state["organizer_tokens"]["access_token"]
    other = ctx.state["other_tokens"]["access_token"]
    path = f"/eventos/{event['id']}"

    assert event["owner_id"] == ctx.state["organizer_id"]
    ctx.request("events", "PUT", path, payload, token=other, expected=404)
    ctx.request("events", "DELETE", path, token=other, expected=404)
    ctx.request("events", "PUT", path, payload, token=owner, expected=200)

    temporal = ctx.create_event()
    baja = ctx.request(
        "events", "DELETE", f"/eventos/{temporal['id']}", token=owner, expected=200
    )
    assert baja["activo"] is False


def inventario_y_reservas(ctx: E2EContext):
    event = ctx.create_event(cupo=10)
    base = f"/eventos/{event['id']}/modalidades/{event['modalidades'][0]['id']}"

    def disponibles() -> int:
        return ctx.request("events", "GET", f"{base}/disponibilidad")["disponibles"]

    assert disponibles() == 10

    clave = {"Idempotency-Key": f"reserva-{uuid.uuid4().hex[:8]}"}
    reserva = ctx.request(
        "events", "POST", f"{base}/reservas", {}, headers=clave, expected=201
    )["reserva_id"]
    assert disponibles() == 9

    repetida = ctx.request(
        "events", "POST", f"{base}/reservas", {}, headers=clave, expected=200
    )
    assert repetida["reserva_id"] == reserva
    assert disponibles() == 9

    confirmada = ctx.request(
        "events", "POST", f"{base}/reservas/{reserva}/confirmar", expected=200
    )
    assert confirmada["status"] == "confirmada"
    ctx.request("events", "DELETE", f"{base}/reservas/{reserva}", expected=409)

    otra = ctx.request("events", "POST", f"{base}/reservas", {}, expected=201)
    assert disponibles() == 8
    liberada = ctx.request(
        "events", "DELETE", f"{base}/reservas/{otra['reserva_id']}", expected=200
    )
    assert liberada["status"] == "liberada"
    assert disponibles() == 9

    ctx.request(
        "events",
        "POST",
        f"/eventos/{uuid.uuid4()}/modalidades/{uuid.uuid4()}/reservas",
        {},
        expected=404,
    )


SCENARIOS = [
    ("catalogo_publico", catalogo_publico),
    ("escritura_protegida", escritura_protegida),
    ("propiedad_y_baja_logica", propiedad_y_baja_logica),
    ("inventario_y_reservas", inventario_y_reservas),
]

if __name__ == "__main__":
    sys.exit(run_scenarios("events-service Compose verification", SCENARIOS))
