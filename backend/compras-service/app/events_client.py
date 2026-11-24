import uuid

import httpx

from app.config import settings


class EventsServiceError(Exception):
    """Eventos no respondió de forma utilizable (red, timeout o 5xx)."""


class EventsConflictError(Exception):
    """Eventos rechazó la operación por conflicto o falta de disponibilidad (409)."""


class EventsClient:
    def __init__(
        self,
        base_url: str,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._transport = transport

    async def obtener_evento(
        self, evento_id: uuid.UUID, correlation_id: str
    ) -> dict | None:
        """Devuelve el evento, o None si Eventos responde 404."""
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.get(
                    f"/eventos/{evento_id}",
                    headers={"X-Correlation-Id": correlation_id},
                )
        except httpx.HTTPError as exc:
            raise EventsServiceError(str(exc)) from exc

        if response.status_code == 404:
            return None
        if response.status_code >= 500:
            raise EventsServiceError(f"status {response.status_code}")
        response.raise_for_status()
        return response.json()

    async def reservar_entrada(
        self,
        evento_id: uuid.UUID,
        modalidad_id: uuid.UUID,
        asiento_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> uuid.UUID:
        """Reserva una entrada o asiento en events-service."""
        headers = {}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        body = {}
        if asiento_id:
            body["asiento_id"] = str(asiento_id)

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    f"/eventos/{evento_id}/modalidades/{modalidad_id}/reservas",
                    json=body,
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise EventsServiceError(str(exc)) from exc

        if response.status_code == 409:
            is_json = response.headers.get("content-type", "").startswith(
                "application/json"
            )
            detail = (
                response.json().get("detail", "conflict") if is_json else "conflict"
            )
            raise EventsConflictError(detail)
        if response.status_code in (200, 201):
            data = response.json()
            return uuid.UUID(data["reserva_id"])
        if response.status_code == 404:
            raise EventsServiceError("not found")
        raise EventsServiceError(f"status {response.status_code}")

    async def confirmar_reserva(
        self,
        evento_id: uuid.UUID,
        modalidad_id: uuid.UUID,
        reserva_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> bool:
        """Confirma una reserva en events-service."""
        headers = {}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    f"/eventos/{evento_id}/modalidades/{modalidad_id}/reservas/{reserva_id}/confirmar",
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise EventsServiceError(str(exc)) from exc

        if response.status_code == 200:
            return True
        if response.status_code == 409:
            is_json = response.headers.get("content-type", "").startswith(
                "application/json"
            )
            detail = (
                response.json().get("detail", "conflict") if is_json else "conflict"
            )
            raise EventsConflictError(detail)
        raise EventsServiceError(f"status {response.status_code}")

    async def liberar_reserva(
        self,
        evento_id: uuid.UUID,
        modalidad_id: uuid.UUID,
        reserva_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> bool:
        """Libera una reserva en events-service (compensación)."""
        headers = {}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.delete(
                    f"/eventos/{evento_id}/modalidades/{modalidad_id}/reservas/{reserva_id}",
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise EventsServiceError(str(exc)) from exc

        if response.status_code in (200, 404, 409):
            # 404 o 409 significa que ya no está activa / ya liberada
            return True
        raise EventsServiceError(f"status {response.status_code}")


def get_events_client() -> EventsClient:
    return EventsClient(settings.events_service_url, settings.events_timeout_seconds)
