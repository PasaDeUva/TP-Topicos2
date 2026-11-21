import uuid

import httpx

from app.config import settings


class EventsServiceError(Exception):
    """Eventos no respondió de forma utilizable (red, timeout o 5xx)."""


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


def get_events_client() -> EventsClient:
    return EventsClient(settings.events_service_url, settings.events_timeout_seconds)
