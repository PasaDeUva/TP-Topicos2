"""Escenario multiservicio: compras fallidas por estado del catálogo e inventario.

Servicios involucrados: identity-service, events-service y compras-service.

Qué valida (fallos cuyo origen está en events-service y que compras-service debe
traducir correctamente al cliente):
1. Evento inexistente: compras consulta a events y responde 404.
2. Modalidad inexistente en un evento real: 404.
3. Evento inactivo (dado de baja por su organizador en events): 409.
4. Cupo agotado: events-service responde 409 al reservar, compras lo propaga al
   cliente y NO persiste la compra fallida (el listado del cliente queda vacío).
"""

import uuid

from harness import E2EContext


def _key() -> dict:
    return {"Idempotency-Key": f"fail-key-{uuid.uuid4().hex[:8]}"}


def run(ctx: E2EContext):
    event = ctx.ensure_event()
    customer = ctx.state["customer_tokens"]["access_token"]
    other = ctx.state["other_customer_tokens"]["access_token"]
    organizer = ctx.state["organizer_tokens"]["access_token"]

    def comprar(evento_id, modalidad_id, token, expected):
        return ctx.request(
            "purchases",
            "POST",
            "/compras",
            {"evento_id": evento_id, "modalidad_id": modalidad_id},
            token=token,
            headers=_key(),
            expected=expected,
        )

    comprar(str(uuid.uuid4()), str(uuid.uuid4()), customer, 404)
    comprar(event["id"], str(uuid.uuid4()), customer, 404)

    temporal = ctx.create_event()
    ctx.request("events", "DELETE", f"/eventos/{temporal['id']}", token=organizer)
    comprar(temporal["id"], temporal["modalidades"][0]["id"], customer, 409)

    limitado = ctx.create_event(cupo=1)
    modalidad = limitado["modalidades"][0]["id"]
    comprar(limitado["id"], modalidad, customer, 201)
    comprar(limitado["id"], modalidad, other, 409)
    assert ctx.request("purchases", "GET", "/compras", token=other) == []
