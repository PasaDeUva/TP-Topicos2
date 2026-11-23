import json
import uuid

import httpx
import pytest
from pydantic import ValidationError

from app.events_client import EventsClient, EventsServiceError
from app.schemas import CompraIn
from tests.conftest import TEST_CUSTOMER_ID


async def test_bitacora_registra_metodo_ruta_estado_y_tiempo(client, capsys):
    correlation = str(uuid.uuid4())

    response = await client.get(
        "/compras",
        params={"cliente_id": str(TEST_CUSTOMER_ID)},
        headers={"X-Correlation-Id": correlation},
    )

    registro = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert registro["method"] == "GET"
    assert registro["path"] == "/compras"
    assert registro["status_code"] == response.status_code == 200
    assert registro["correlation_id"] == correlation
    assert registro["duration_ms"] >= 0
    assert response.headers["X-Correlation-Id"] == correlation


def _cliente_con(handler) -> EventsClient:
    return EventsClient(
        "http://events", timeout=1.0, transport=httpx.MockTransport(handler)
    )


async def test_cliente_devuelve_evento_ante_200_y_reenvia_correlation_id():
    evento = {"id": "x", "activo": True}
    recibidos = []

    def handler(request: httpx.Request) -> httpx.Response:
        recibidos.append(request.headers["X-Correlation-Id"])
        return httpx.Response(200, json=evento)

    resultado = await _cliente_con(handler).obtener_evento(uuid.uuid4(), "abc")

    assert resultado == evento
    assert recibidos == ["abc"]


async def test_cliente_devuelve_none_ante_404():
    cliente = _cliente_con(lambda request: httpx.Response(404))
    assert await cliente.obtener_evento(uuid.uuid4(), "abc") is None


async def test_cliente_lanza_error_propio_ante_500():
    cliente = _cliente_con(lambda request: httpx.Response(500))
    with pytest.raises(EventsServiceError):
        await cliente.obtener_evento(uuid.uuid4(), "abc")


async def test_cliente_lanza_error_propio_ante_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("tiempo agotado", request=request)

    with pytest.raises(EventsServiceError):
        await _cliente_con(handler).obtener_evento(uuid.uuid4(), "abc")


def test_compra_in_rechaza_uuid_invalido_y_campos_faltantes():
    with pytest.raises(ValidationError):
        CompraIn(
            cliente_id="no-uuid",
            evento_id=str(uuid.uuid4()),
            modalidad_id=str(uuid.uuid4()),
        )
    with pytest.raises(ValidationError):
        CompraIn(cliente_id=str(uuid.uuid4()), evento_id=str(uuid.uuid4()))
