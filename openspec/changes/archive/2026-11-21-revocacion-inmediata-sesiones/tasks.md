# Tasks

## 1. Decisión y contrato

- [x] 1.1 Crear un ADR propuesto en `docs/adr/` que documente la nueva validación, su relación con ADR-0004, alternativas, transición y costos; verificar numeración y enlace desde el diseño.
- [x] 1.2 Definir y documentar el contrato interno autenticado para verificar el token completo y la sesión, incluyendo permisos, fallos y prohibición de registrar credenciales; verificar ejemplos y respuestas contra las pruebas de API.

## 2. Identity y sesiones

- [x] 2.1 Asociar los JWT nuevos a su sesión y validar titular, firma, vencimiento y sesión vigente; probar tokens válidos, antiguos sin sesión, alterados y con asociación incorrecta.
- [x] 2.2 Rechazar tokens tras cierre, vencimiento o revocación por reutilización, sin afectar otras sesiones; probar ambos contratos web y JSON y carreras de autorización posteriores al cierre.
- [x] 2.3 Implementar verificación interna para servicios autorizados con rechazo ante credenciales o tokens inválidos y errores cerrados; probar también que no se exponen tokens en respuestas ni registros.

## 3. Compatibilidad y verificación

- [x] 3.1 Verificar restauración, renovación y errores de sesión web con tokens anteriores, incluyendo coordinación entre pestañas; ejecutar pruebas enfocadas del cliente.
- [x] 3.2 Actualizar documentación de consumidores y migración sin afirmar que Eventos o Compras estén integrados; verificar consistencia con el ADR y los contratos existentes.
- [x] 3.3 Ejecutar suites de Identity y frontend y un flujo HTTP web en datos aislados, cubriendo cierre y reutilización de token previo; registrar resultados.
- [x] 3.4 Verificar despliegue y reversión aislados, documentando la ventana de seguridad reabierta por la reversión y sin afectar servicios, datos ni secretos ajenos sin autorización.
