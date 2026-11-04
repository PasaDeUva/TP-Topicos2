# Tasks

## 3. Bloque 3 — Compras, pagos e historial

Dependencias: consumir los contratos del servicio Identity del Bloque 1 y del inventario del servicio Events del Bloque 2. No acceder directamente a sus bases de datos.

- [ ] 3.1 Crear el servicio Purchases en FastAPI con SQLAlchemy, base lógica propia y Dockerfile; verificar arranque, conexión y endpoint de salud.
- [ ] 3.2 Crear modelos y migraciones para compras, líneas con snapshots de evento/precio y PaymentAttempt; verificar persistencia con pruebas de servicio.
- [ ] 3.3 Implementar checkout con el servicio Events para reservar todas las entradas, sin acceso directo a su base; verificar idempotencia, rechazo sin compra parcial y reserva atómica con pruebas de integración.
- [ ] 3.4 Implementar el simulador de pago Pendiente/Exitoso/Fallido, reintentos sobre la misma compra y confirmación de reservas activas; verificar estados y emisiones únicas con pruebas de API.
- [ ] 3.5 Implementar vencimiento/reconciliación, liberación de inventario y Revisión requerida para pagos tardíos; verificar liberación a los 10 minutos y ausencia de emisión de entradas tardía.
- [ ] 3.6 Implementar la API Mis Compras filtrada por cliente, con todos los estados, orden descendente y datos históricos; verificar privacidad, estados y estado vacío con pruebas de API.
- [ ] 3.7 Crear mockups y vistas React para checkout y Mis Compras; verificar estados de pago, reintentos, disponibilidad y ausencia de datos individuales de asistentes con pruebas de UI.
- [ ] 3.8 Añadir pruebas de integración entre Identity, Events y Purchases para concurrencia, notificaciones repetidas, inicio del evento con reservas activas y fallos/reintentos de servicio.
- [ ] 3.9 Documentar contratos REST de compras e instrumentar bitácora HTTP con autenticación, resultado y duración; verificar contratos y registros.
- [ ] 3.10 Actualizar la bitácora del proyecto con decisiones, pruebas y dependencias entre bloques; verificar que los pasos de checkout e integración queden documentados.
