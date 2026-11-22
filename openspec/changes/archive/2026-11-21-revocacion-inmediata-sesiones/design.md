# Design

## Context

Identity almacena sesiones con cuenta, vencimiento y revocación, pero sus JWT solo identifican la cuenta. `current_account` valida firma y claims sin consultar la sesión. El ADR-0004 aceptado admite la validación local de tokens hasta su vencimiento; esta propuesta cambia esa garantía.

## Goals / Non-Goals

**Goals:** revocar nuevas autorizaciones en Identity y proporcionar un contrato verificable a futuros consumidores, manteniendo sesiones independientes.

**Non-Goals:** integrar Eventos o Compras, proteger sus endpoints actuales o afirmar que sus verificaciones locales ya ofrecen revocación inmediata.

## Decisions

- Emitir un identificador de sesión firmado en cada JWT de inicio y renovación. Identity validará firma, claims y vínculo cuenta-sesión, además de comprobar que la sesión exista, no esté revocada y no haya vencido. Rechazará tokens sin ese identificador; no intentará inferir su sesión.
- Usar la sesión persistida como fuente de verdad. No usar una caché que pueda conservar un estado activo después de la revocación; ante indisponibilidad de la verificación, no autorizar nuevas operaciones protegidas.
- Incorporar `POST /internal/sessions/verify` para futuros consumidores: recibe `{"access_token":"..."}` en el cuerpo y las credenciales `X-Service-Id` y `X-Service-Token`; requiere permiso explícito `sessions_read`. Devuelve `200` con `account_id` solo si el JWT completo y su sesión son válidos; `400` indica entrada malformada, `401` credenciales de servicio o token inválidos, `403` falta de permiso y `503` configuración de autenticación no disponible. No registrar tokens ni enviarlos en URL. Mantener separada la consulta actual de roles y exigir ambas comprobaciones cuando corresponda. Las configuraciones existentes sin `sessions_read` conservan su acceso previo a roles, pero no conceden el permiso nuevo.
- Una operación autorizada antes de que la revocación sea efectiva puede finalizar. La garantía se aplica a nuevas autorizaciones posteriores; las demás sesiones de la misma cuenta permanecen independientes.
- La decisión y su relación con ADR-0004 se documentan en [ADR-0011 aceptado](../../../docs/adr/0011-revocacion-inmediata-sesiones.md), incluyendo disponibilidad, migración y seguridad.

## Risks / Trade-offs

- [Tokens anteriores] → rechazarlos al activar el cambio; comunicar que la web puede solicitar un nuevo ingreso y que clientes API pueden renovar si su credencial sigue vigente.
- [Disponibilidad y carga de Identity] → fallar cerrado; medir la dependencia y no prometer autorización sin conexión. La integración de consumidores concretos queda para otro cambio.
- [Carreras entre cierre y autorización] → probar que las autorizaciones iniciadas después de la revocación efectiva se rechacen, sin cancelar operaciones ya autorizadas.
- [Exposición de credenciales] → requerir autenticación de servicio, canal protegido y prohibir tokens en URL, registros y mensajes de error.

## Migration Plan

Revisar y documentar el ADR y el contrato antes del despliegue. Probar en un entorno aislado, comunicar el rechazo de JWT anteriores y desplegar Identity con emisión y validación coherentes. La reversión al comportamiento anterior reabre la ventana de validez hasta el vencimiento del JWT; debe explicitarse ese riesgo y no revocar o borrar datos ajenos como efecto de la prueba.

## Verification

- Identity: 75 pruebas y Ruff pasaron en PostgreSQL aislado; el frontend pasó 50 pruebas, lint y build.
- Playwright aislado verificó rechazo del token tras cierre y propagación entre pestañas. Otro escenario inició una sesión con Identity anterior, actualizó el servicio, comprobó el rechazo del token antiguo y restauró la sesión por renovación en dos pestañas.
- La reversión aislada confirmó cierre exitoso en la versión anterior y aceptación de su token previo; se restauró la versión nueva y se verificó nuevamente el rechazo posterior al cierre.
