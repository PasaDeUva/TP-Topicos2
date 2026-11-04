# Tasks

## 2. Bloque 2 — Eventos y catálogo

Dependencia: usar el contrato de identidad del Bloque 1. Publicar el contrato de reserva/confirmación/liberación de inventario para que lo consuma el Bloque 3.

- [ ] 2.1 Crear el servicio Events en FastAPI con SQLAlchemy, base lógica propia y Dockerfile; verificar el arranque, conexión y endpoint de salud.
- [ ] 2.2 Crear modelos y migraciones para eventos, metadatos opcionales, modalidades de entrada, asientos, zonas y ofertas; verificar persistencia de datos numerados y no numerados.
- [ ] 2.3 Implementar borradores, validación de publicación, publicación explícita, inicio programado de venta y ocultamiento al día siguiente; verificar transiciones con pruebas de API.
- [ ] 2.4 Implementar pausa/despublicación por administrador y organizador, reanudación/republicación y restricciones de edición; verificar cambios permitidos y rechazados con pruebas de API.
- [ ] 2.5 Implementar consulta de disponibilidad y operaciones idempotentes de reserva/confirmación/liberación; verificar exclusividad de asientos y límites de capacidad por zona.
- [ ] 2.6 Implementar expiración de reservas a los 10 minutos y manejo de concurrencia con transacciones InnoDB; verificar expiración y ausencia de doble venta con pruebas concurrentes.
- [ ] 2.7 Crear mockups y vistas React para gestión del organizador, moderación administrativa y catálogo/ficha pública; verificar estados y disponibilidad con pruebas de UI.
- [ ] 2.8 Documentar los contratos REST de eventos e inventario para el Bloque 3 e instrumentar bitácora HTTP con resultado y duración; verificar el contrato OpenAPI y los registros.
- [ ] 2.9 Actualizar la bitácora del proyecto con las decisiones y pruebas del Bloque 2; verificar que incluya el contrato de reserva compartido.
