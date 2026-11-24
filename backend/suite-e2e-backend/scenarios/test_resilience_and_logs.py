"""Escenario multiservicio: Resiliencia ante fallos, degradación controlada y seguridad de bitácoras.

Servicios involucrados:
- identity-service: Servicio central de autenticación y tokens.
- events-service: Consumidor dependiente de identity.
- compras-service: Consumidor dependiente de identity.

Escenarios que valida este test:
1. Fallo de Credenciales Interservicio (Mismatched Service Token):
   - Se simula una mala configuración actualizando compras-service con un token de servicio inválido.
   - Al intentar autenticar peticiones de clientes, compras-service no puede consultar identity-service
     y responde 503 Service Unavailable de forma controlada.
   - Al restablecer el token legítimo, el servicio se recupera automáticamente.
2. Indisponibilidad Total de Identity Service:
   - Se detiene el contenedor de identity-service (simulando una caída total del servicio de autenticación).
   - Tanto events-service como compras-service detectan la indisponibilidad al intentar validar sesiones/roles
     y responden con 503 Service Unavailable, evitando estados inconsistentes o accesos no autorizados.
3. Auditoría de Seguridad de Bitácoras (Zero-Leakage):
   - Se extraen y analizan las bitácoras completas de los tres servicios (identity, events y compras).
   - Se verifica rigurosamente que ninguna contraseña de usuario, token de servicio, token de acceso JWT
     ni refresh token haya quedado expuesto en texto plano en la salida estándar de los contenedores.
"""

import secrets

from harness.client import wait_ready
from harness.context import E2EContext
from harness.security import assert_no_secrets_in_logs


def run(ctx: E2EContext):
    """Verify service degradation on bad service token, identity outage (503) and zero secret leaks."""
    ctx.ensure_event()
    event = ctx.state["event"]
    org_token = ctx.state["organizer_tokens"]["access_token"]
    other_customer_tokens = ctx.state["other_customer_tokens"]

    # Test 1: Interservice authentication failure
    ctx.env["IDENTITY_PURCHASES_SERVICE_TOKEN"] = secrets.token_hex(32)
    ctx.compose("up", "-d", "--no-deps", "--force-recreate", "--wait", "compras-service")
    ctx.refresh_urls()
    wait_ready(ctx.purchases_url, "/compras", expected=401)

    ctx.request(
        "purchases",
        "GET",
        "/compras",
        token=other_customer_tokens["access_token"],
        expected=503,
    )

    # Restore correct service token
    ctx.env["IDENTITY_PURCHASES_SERVICE_TOKEN"] = ctx.purchases_secret
    ctx.compose("up", "-d", "--no-deps", "--force-recreate", "--wait", "compras-service")
    ctx.refresh_urls()
    wait_ready(ctx.purchases_url, "/compras", expected=401)

    # Test 2: Complete Identity service downtime
    ctx.compose("stop", "identity-service")

    ctx.request(
        "events",
        "DELETE",
        f"/eventos/{event['id']}",
        token=org_token,
        expected=503,
    )
    ctx.request(
        "purchases",
        "GET",
        "/compras",
        token=other_customer_tokens["access_token"],
        expected=503,
    )

    # Test 3: Log audit for secret leakage
    logs = ctx.fetch_logs("identity-service", "events-service", "compras-service")
    assert_no_secrets_in_logs(logs, ctx.get_all_secrets())
