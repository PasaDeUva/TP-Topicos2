# Design

## Context

Identity ya comprueba el rol administrador activo en `PATCH /admin/organizers/{account_id}/status`; `/auth/me` solo devuelve la cuenta propia. El cliente conserva el token de acceso en memoria y CORS admite actualmente GET y POST. Ver `proposal.md` y ADR-0010.

## Goals / Non-Goals

**Goals:** preservar las reglas de sesión y autorización existentes y minimizar los datos expuestos.

**Non-Goals:** cambiar roles de cliente, crear administración general de cuentas o modificar contratos existentes.

## Decisions

- Aplicar la propuesta de [ADR-0010](../../../docs/adr/0010-consulta-administrativa-organizadores.md): agregar `GET /admin/organizers` con identificador, email y estado; comprobar el rol vigente en cada consulta. El endpoint existente sigue verificando el rol al mutar, aunque la web lo oculte a no administradores.
- Ordenar por email e identificador de forma estable; incluir estados pendientes, habilitados y deshabilitados. Para el alcance académico inicial se propone una lista sin paginación; evitar afirmar que existe una fecha de solicitud, que el modelo no almacena.
- Reutilizar el PATCH existente y permitir ese método en CORS para los orígenes configurados. Una petición rechazada no concede permisos y no se amplían orígenes ni cabeceras arbitrariamente.
- La vista reutiliza la sesión en memoria; invalida sesión ante 401, oculta datos administrativos ante 403 y descarta respuestas obsoletas al cambiar token o desmontarse. Después de una mutación, muestra el estado confirmado o vuelve a consultar ante resultado incierto.
- Mostrar estados de carga, vacío, error y progreso, con controles accesibles y diseño adaptable. No incluir filtros ni datos ficticios.

## Risks / Trade-offs

- [Exposición de datos] → comprobar rol vigente en el servidor y devolver solo datos necesarios; probar ausencia de credenciales.
- [Cambios simultáneos o respuesta perdida] → no asumir éxito; volver a consultar ante resultado incierto y respetar la respuesta del servidor.
- [Lista creciente] → la lista completa simplifica esta etapa; evaluar paginación antes de necesidades de escala superiores.
- [Sesión o permisos cambiados] → no conservar ni mostrar información administrativa después de 401/403 o cambio de sesión.

## Migration Plan

Desplegar primero Identity compatible con el endpoint y CORS, después el frontend. Para revertir, retirar primero el frontend nuevo y luego el endpoint aditivo; no se requiere migración de datos. Conservar configuración y secretos existentes.
