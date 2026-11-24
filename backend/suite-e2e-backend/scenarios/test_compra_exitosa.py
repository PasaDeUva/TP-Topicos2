"""Escenario multiservicio: compra exitosa y orquestación entre servicios.

Servicios involucrados: identity-service, events-service y compras-service.

Qué valida (solo lo que requiere a los tres servicios a la vez):
1. Compra de un cliente autenticado: compras-service valida la sesión con
   identity-service, consulta el evento en events-service y responde 201 con
   estado 'confirmada', reserva_id y el cliente_id del token.
2. Compra en modalidad numerada: reserva y compra con asiento_id asignado, y
   conflicto 409 al reintentar el mismo asiento.
3. Orquestación de inventario: la compra reserva y confirma en events-service,
   por lo que la disponibilidad de la modalidad baja exactamente en 1.
4. Idempotencia extremo a extremo: el replay con la misma Idempotency-Key devuelve
   200 con la misma compra y NO consume otra unidad de inventario en events-service.
5. Trazabilidad: el X-Correlation-Id viaja entre servicios y queda en las
   bitácoras JSON de events-service y compras-service (método, ruta, status,
   duración).
"""

import uuid

from harness import E2EContext


def run(ctx: E2EContext):
    event = ctx.ensure_event()
    customer_id = ctx.state["customer_id"]
    customer_tokens = ctx.state["customer_tokens"]
    event_correlation = ctx.state["event_correlation"]
    modalidad_id = event["modalidades"][0]["id"]
    disponibilidad_path = (
        f"/eventos/{event['id']}/modalidades/{modalidad_id}/disponibilidad"
    )

    def disponibles() -> int:
        return ctx.request("events", "GET", disponibilidad_path)["disponibles"]

    inicial = disponibles()
    body = {"evento_id": event["id"], "modalidad_id": modalidad_id}
    key = {"Idempotency-Key": f"integration-key-{uuid.uuid4().hex[:8]}"}
    purchase_correlation = str(uuid.uuid4())

    purchase = ctx.request(
        "purchases",
        "POST",
        "/compras",
        body,
        token=customer_tokens["access_token"],
        headers={**key, "X-Correlation-Id": purchase_correlation},
        expected=201,
    )
    assert purchase["cliente_id"] == customer_id
    assert purchase["estado"] == "confirmada"
    assert "reserva_id" in purchase
    assert purchase["asiento_id"] is None
    assert disponibles() == inicial - 1

    repeated = ctx.request(
        "purchases",
        "POST",
        "/compras",
        body,
        token=customer_tokens["access_token"],
        headers=key,
        expected=200,
    )
    assert repeated["id"] == purchase["id"]
    assert disponibles() == inicial - 1

    modalidad_num = next(
        (m for m in event["modalidades"] if m["tipo"] == "numerado"), None
    )
    if modalidad_num and modalidad_num.get("sectores"):
        asiento_target = modalidad_num["sectores"][0]["asientos"][0]["id"]
        key_num = {"Idempotency-Key": f"integration-num-key-{uuid.uuid4().hex[:8]}"}
        purchase_num = ctx.request(
            "purchases",
            "POST",
            "/compras",
            {
                "evento_id": event["id"],
                "modalidad_id": modalidad_num["id"],
                "asiento_id": asiento_target,
            },
            token=customer_tokens["access_token"],
            headers=key_num,
            expected=201,
        )
        assert purchase_num["asiento_id"] == asiento_target
        assert purchase_num["estado"] == "confirmada"

        key_num_dup = {"Idempotency-Key": f"integration-num-key-2-{uuid.uuid4().hex[:8]}"}
        ctx.request(
            "purchases",
            "POST",
            "/compras",
            {
                "evento_id": event["id"],
                "modalidad_id": modalidad_num["id"],
                "asiento_id": asiento_target,
            },
            token=customer_tokens["access_token"],
            headers=key_num_dup,
            expected=409,
        )
        ctx.state["purchase_num"] = purchase_num

    compras = ctx.request(
        "purchases", "GET", "/compras", token=customer_tokens["access_token"]
    )
    compras_ids = [c["id"] for c in compras]
    assert purchase["id"] in compras_ids
    if "purchase_num" in ctx.state:
        assert ctx.state["purchase_num"]["id"] in compras_ids

    for service, correlation, method, path, status in (
        ("events-service", event_correlation, "POST", "/eventos", 201),
        ("events-service", purchase_correlation, "GET", f"/eventos/{event['id']}", 200),
        ("compras-service", purchase_correlation, "POST", "/compras", 201),
    ):
        records = ctx.parse_service_json_logs(service)
        assert any(
            record.get("correlation_id") == correlation
            and record.get("method") == method
            and record.get("path") == path
            and record.get("status_code") == status
            and isinstance(record.get("duration_ms"), (int, float))
            for record in records
        ), f"Falta log estructurado en {service}: {method} {path} ({correlation})"

    ctx.state["purchase"] = purchase
    ctx.state["purchase_body"] = body
    ctx.state["purchase_key"] = key
    ctx.state["purchase_correlation"] = purchase_correlation
