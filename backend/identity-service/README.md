# Identity Service

Servicio de cuentas, roles y sesiones. El entorno local usa PostgreSQL separado para desarrollo y pruebas.

## Arranque local

Desde la raíz del repositorio:

```sh
docker compose up -d --build --wait identity-service
curl http://localhost:8002/health
```

La respuesta esperada es `{"status":"ok"}`. El arranque aplica las migraciones y crea el administrador si todavía no existe. Los valores locales predeterminados son `admin@example.com` y `local-admin-password`; se reemplazan mediante `IDENTITY_ADMIN_EMAIL` e `IDENTITY_ADMIN_PASSWORD`. Reiniciar el servicio no restablece su contraseña.

Las claves RSA se generan una sola vez y se conservan en volúmenes separados: `identity-private-keys` y `identity-public-keys`. Solo Identity monta la clave privada. Los valores locales se pueden reemplazar mediante `IDENTITY_JWT_ISSUER`, `IDENTITY_JWT_AUDIENCE`, `IDENTITY_EVENTS_SERVICE_TOKEN`, `IDENTITY_PURCHASES_SERVICE_TOKEN` o `IDENTITY_SERVICE_CREDENTIALS_JSON`. La configuración de Compose es para desarrollo local; otros entornos deben proporcionar sus propias claves, credenciales y parámetros.

Para recuperar la contraseña del administrador configurado, ejecutar en una terminal interactiva:

```sh
docker compose exec identity-service python -m app.admin recover
```

La recuperación revoca las sesiones de ese administrador y sus credenciales de renovación. Los JWT de acceso ya emitidos pueden seguir siendo válidos hasta su vencimiento.

## Pruebas

```sh
docker compose build backend-tests
docker compose run --rm backend-tests
docker compose run --rm --no-deps backend-tests python -m ruff check mock-service identity-service
```

El runner inicia la base de pruebas y aplica las migraciones antes de ejecutar la suite. La base `identity_test` es independiente de `identity_db`.

## Flujo HTTP

Con el servicio iniciado:

1. `POST /auth/register` con email, contraseña y rol `organizador` devuelve `201` y el rol `pendiente`.
2. `POST /auth/login` devuelve `200`, un JWT y una credencial de renovación. `POST /auth/refresh` devuelve nuevas credenciales; reutilizar la anterior revoca la sesión.
3. Un administrador autenticado usa `PATCH /admin/organizers/{account_id}/status` con `{"status":"habilitado"}` y recibe `200`.
4. Un servicio autorizado consulta `GET /internal/accounts/{account_id}/roles` y recibe el estado actualizado. `POST /auth/logout` revoca la renovación y devuelve `204`.

Las rutas, estructuras y errores completos están en el diseño de `openspec/changes/gestion-de-accesos/design.md`. La validación que deberán aplicar los consumidores está en [CONSUMERS.md](CONSUMERS.md).
