"""Verificación de caja negra de compras-service sobre Compose aislado.

Escenarios AISLADOS de compras-service: validan reglas propias del servicio
(autenticación/rol, validación de entrada, idempotencia, propiedad de compras).
Identity solo emite tokens y events-service solo provee un evento de datos; la
orquestación de reserva/confirmación entre servicios se valida en
backend/suite-e2e-backend/.

Escenarios:
1. Autenticación requerida: sin token 401 y rol organizador 403.
2. Validación de entrada: falta Idempotency-Key 400, cuerpo inválido 400,
   cliente_id ajeno 403.
3. Idempotencia y propiedad: compra 201, replay 200, conflicto 409, consulta
   propia 200, ajena 404 y listado del cliente.
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "suite-e2e-backend"))

from harness import E2EContext, run_scenarios  # noqa: E402


def _clave() -> dict:
    return {"Idempotency-Key": f"compras-{uuid.uuid4().hex[:8]}"}


def autenticacion_requerida(ctx: E2EContext):
    ctx.ensure_users()
    body = {"evento_id": str(uuid.uuid4()), "modalidad_id": str(uuid.uuid4())}
    organizer = ctx.state["organizer_tokens"]["access_token"]

    ctx.request("purchases", "POST", "/compras", body, headers=_clave(), expected=401)
    ctx.request("purchases", "GET", "/compras", expected=401)
    ctx.request(
        "purchases", "POST", "/compras", body, token=organizer,
        headers=_clave(), expected=403,
    )
    ctx.request("purchases", "GET", "/compras", token=organizer, expected=403)


def validacion_de_entrada(ctx: E2EContext):
    ctx.ensure_users()
    token = ctx.state["customer_tokens"]["access_token"]
    body = {"evento_id": str(uuid.uuid4()), "modalidad_id": str(uuid.uuid4())}

    ctx.request("purchases", "POST", "/compras", body, token=token, expected=400)
    ctx.request(
        "purchases", "POST", "/compras", {}, token=token,
        headers=_clave(), expected=400,
    )
    ajeno = {**body, "cliente_id": ctx.state["other_customer_id"]}
    ctx.request(
        "purchases", "POST", "/compras", ajeno, token=token,
        headers=_clave(), expected=403,
    )


def idempotencia_y_propiedad(ctx: E2EContext):
    event = ctx.ensure_event()
    token = ctx.state["customer_tokens"]["access_token"]
    other = ctx.state["other_customer_tokens"]["access_token"]
    body = {"evento_id": event["id"], "modalidad_id": event["modalidades"][0]["id"]}
    clave = _clave()

    compra = ctx.request(
        "purchases", "POST", "/compras", body, token=token, headers=clave, expected=201
    )
    assert compra["cliente_id"] == ctx.state["customer_id"]
    assert compra["estado"] == "confirmada"
    assert "reserva_id" in compra
    assert compra["asiento_id"] is None

    repetida = ctx.request(
        "purchases", "POST", "/compras", body, token=token, headers=clave, expected=200
    )
    assert repetida["id"] == compra["id"]
    distinta = {**body, "evento_id": str(uuid.uuid4())}
    ctx.request(
        "purchases", "POST", "/compras", distinta, token=token,
        headers=clave, expected=409,
    )

    propia = ctx.request("purchases", "GET", f"/compras/{compra['id']}", token=token)
    assert propia["id"] == compra["id"]
    ctx.request(
        "purchases", "GET", f"/compras/{compra['id']}", token=other, expected=404
    )
    listado = ctx.request("purchases", "GET", "/compras", token=token)
    assert [item["id"] for item in listado] == [compra["id"]]
    assert ctx.request("purchases", "GET", "/compras", token=other) == []


SCENARIOS = [
    ("autenticacion_requerida", autenticacion_requerida),
    ("validacion_de_entrada", validacion_de_entrada),
    ("idempotencia_y_propiedad", idempotencia_y_propiedad),
]

if __name__ == "__main__":
    sys.exit(run_scenarios("compras-service Compose verification", SCENARIOS))
