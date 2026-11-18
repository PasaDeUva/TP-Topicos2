# Identity Service

Servicio de cuentas, roles y sesiones. El entorno local usa una instancia PostgreSQL con bases separadas para desarrollo y pruebas.

## Arranque local

Desde la raíz del repositorio:

```sh
docker compose up -d --build --wait identity-service
curl http://localhost:8002/health
```

La respuesta esperada es `{"status":"ok"}`. El arranque aplica las migraciones y crea el administrador si todavía no existe. Los valores locales predeterminados son `admin@example.com` y `local-admin-password`; se reemplazan mediante `IDENTITY_ADMIN_EMAIL` e `IDENTITY_ADMIN_PASSWORD`. Reiniciar el servicio no restablece su contraseña.

Compose monta el código local y habilita `--reload`: los cambios en `app/` reinician el servidor. Los cambios de dependencias requieren reconstruir la imagen con `--build`. En Windows y macOS se usa polling para detectar cambios; se puede configurar con `IDENTITY_WATCHFILES_FORCE_POLLING`.

Las claves RSA se generan una sola vez y se conservan en volúmenes separados: `identity-private-keys` y `identity-public-keys`. Solo Identity monta la clave privada. Los valores locales se pueden reemplazar mediante `IDENTITY_JWT_ISSUER`, `IDENTITY_JWT_AUDIENCE`, `IDENTITY_EVENTS_SERVICE_TOKEN`, `IDENTITY_PURCHASES_SERVICE_TOKEN` o `IDENTITY_SERVICE_CREDENTIALS_JSON`. La configuración de Compose es para desarrollo local; otros entornos deben proporcionar sus propias claves, credenciales y parámetros.

Para recuperar la contraseña del administrador configurado, ejecutar en una terminal interactiva:

```sh
docker compose exec identity-service python -m app.admin recover
```

La recuperación revoca las sesiones de ese administrador y sus credenciales de renovación. Los JWT de acceso ya emitidos pueden seguir siendo válidos hasta su vencimiento.

Las contraseñas nuevas admiten entre 8 y 1024 caracteres; login acepta hasta 1024. Las credenciales de renovación admiten hasta 256 caracteres. Esos límites de campos no sustituyen un límite de tamaño del cuerpo HTTP ni controles de tráfico en el despliegue.

## Pruebas

```sh
docker compose build backend-tests
docker compose run --rm backend-tests
docker compose run --rm --no-deps backend-tests python -m ruff check mock-service identity-service
```

El runner inicia las bases de pruebas y crea `identity_test` si falta, incluso en un volumen existente. La suite de Identity aplica sus migraciones antes de ejecutarse. `IDENTITY_TEST_DATABASE_URL` debe apuntar a una base PostgreSQL llamada `identity_test`, independiente de `identity_db` y de la base de Events. `identity_db` e `identity_test` comparten la instancia local de Identity.

Para verificar el contenedor real y el flujo HTTP en un proyecto Compose aislado:

```sh
python backend/identity-service/scripts/verify_compose.py
```

La prueba usa una copia temporal del código, crea y elimina sus propios contenedores y volúmenes, y verifica también la recarga al editar el código.

## Flujo HTTP

Con el servicio iniciado:

1. `POST /auth/register` con email, contraseña y rol `organizador` devuelve `201` y el rol `pendiente`.
2. `POST /auth/login` devuelve `200`, un JWT y una credencial de renovación. `POST /auth/refresh` devuelve nuevas credenciales; reutilizar la anterior revoca la sesión.
3. Un administrador autenticado usa `PATCH /admin/organizers/{account_id}/status` con `{"status":"habilitado"}` y recibe `200`.
4. Un servicio autorizado consulta `GET /internal/accounts/{account_id}/roles` y recibe el estado actualizado. `POST /auth/logout` revoca la renovación y devuelve `204`.

Las rutas, estructuras y errores completos están en el diseño de `openspec/changes/gestion-de-accesos/design.md`. La validación que deberán aplicar los consumidores está en [CONSUMERS.md](CONSUMERS.md).

## Bitácora HTTP

Cada solicitud genera en stdout un registro JSON con método, ruta, estado, duración e identificador de correlación. Identity propaga `X-Correlation-Id` cuando se recibe o genera un UUID cuando falta; también lo devuelve ante errores inesperados. No se registran cuerpos, cabeceras, parámetros de consulta ni detalles de excepciones.
