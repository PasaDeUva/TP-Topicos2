"""Escenario multiservicio: Ciclo de vida de sesiones, revocación inmediata y deshabilitación.

Servicios involucrados:
- identity-service: Gestión de sesiones, endpoints de logout y control administrativo de cuentas.
- events-service: Verificación de permisos vigentes para organizadores.
- compras-service: Verificación de validez de sesiones de clientes ante consultas.

Escenarios que valida este test:
1. Eliminación Lógica de Eventos (Soft Delete):
   - El organizador elimina un evento temporal vía DELETE /eventos/{id}.
   - events-service actualiza el recurso marcándolo como 'activo: false' en lugar de destruirlo físicamente.
2. Revocación Inmediata de Sesión por Logout:
   - El cliente ejecuta un cierre de sesión vía POST /auth/logout en identity-service enviando su refresh_token.
   - De inmediato, el access_token previo queda revocado. Al intentar consultar compras en compras-service
     (GET /compras), identity-service informa que la sesión no es válida y compras-service responde 401 Unauthorized.
3. Deshabilitación Administrativa de Organizadores:
   - El administrador desactiva la cuenta del organizador vía PATCH /admin/organizers/{id}/status con estado 'deshabilitado'.
   - En tiempo real, cualquier operación posterior del organizador en events-service (DELETE /eventos/{id})
     es rechazada con 403 Forbidden tras verificar el estado actualizado con identity-service.
"""

from harness.context import E2EContext


def run(ctx: E2EContext):
    """Verify event soft deletion, session invalidation via logout and organizer deactivation."""
    ctx.ensure_event()
    event = ctx.state["event"]
    event_payload = ctx.state["event_payload"]
    organizer_id = ctx.state["organizer_id"]
    organizer_tokens = ctx.state["organizer_tokens"]
    customer_tokens = ctx.state["customer_tokens"]
    admin_token = ctx.admin_token

    org_token = organizer_tokens["access_token"]

    # Soft deletion of an event
    temporary = ctx.request(
        "events",
        "POST",
        "/eventos",
        event_payload,
        token=org_token,
        expected=201,
    )
    deleted = ctx.request(
        "events",
        "DELETE",
        f"/eventos/{temporary['id']}",
        token=org_token,
        expected=200,
    )
    assert deleted["activo"] is False

    # Immediate session revocation on logout
    ctx.request(
        "identity",
        "POST",
        "/auth/logout",
        {"refresh_token": customer_tokens["refresh_token"]},
        expected=204,
    )
    # Revoked customer access token must be rejected by purchases-service
    ctx.request(
        "purchases",
        "GET",
        "/compras",
        token=customer_tokens["access_token"],
        expected=401,
    )

    # Disable organizer via admin API
    ctx.request(
        "identity",
        "PATCH",
        f"/admin/organizers/{organizer_id}/status",
        {"status": "deshabilitado"},
        token=admin_token,
        expected=200,
    )
    # Disabled organizer cannot perform administrative operations on events (403)
    ctx.request(
        "events",
        "DELETE",
        f"/eventos/{event['id']}",
        token=org_token,
        expected=403,
    )
