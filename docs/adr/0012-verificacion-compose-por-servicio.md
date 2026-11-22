# ADR-0012: Verificación de caja negra con Compose en cada servicio

- Estado: Aceptado
- Fecha: 2026-11-21

## Contexto

Los tests unitarios e in-process de cada servicio usan transportes simulados o bases en memoria. Con ellos no se verifica que los contenedores reales, las bases de datos, las migraciones y la comunicación HTTP entre servicios funcionen juntos. Una revisión del PR #14 señaló este hueco en `compras-service`, que tenía tareas marcadas como integradas sin una prueba automatizada contra Compose.

`identity-service` ya incluye [verify_compose.py](../../backend/identity-service/scripts/verify_compose.py), que levanta el servicio con sus dependencias en un proyecto Compose aislado y verifica el flujo por HTTP real. `compras-service` siguió el mismo patrón, y `events-service` lo incorpora ahora.

## Decisión

Cada servicio backend que expone una API HTTP y tiene base de datos debe incluir un script `scripts/verify_compose.py` que:

1. Copia el código del servicio y de sus dependencias HTTP a un directorio temporal y normaliza los `.sh` a LF, para no depender de cómo Git escribió los finales de línea en Windows.
2. Levanta el servicio con sus bases en un proyecto Compose aislado (`docker compose -p <proyecto-único>`), con puertos publicados aleatorios (`0`) mediante variables de entorno.
3. Ejecuta el flujo principal del servicio por HTTP real y comprueba códigos de respuesta y contenido.
4. Revisa la bitácora de solicitudes en `stdout` y que el `correlation_id` aparezca en ella.
5. Baja el proyecto y sus volúmenes en un bloque `finally`, aunque el flujo falle.

El script usa solo la biblioteca estándar de Python y se ejecuta en el host. Cada script se corre en CI como un paso propio después de los tests de backend. El puerto de cada servicio en `compose.yaml` se parametriza con una variable y un valor por defecto para no chocar con el stack de desarrollo.

Los tests unitarios siguen siendo la primera línea de verificación. Este script no los reemplaza: valida la integración real.

## Consecuencias

### Positivas

- Un cambio que rompe el arranque del contenedor, una migración o el contrato HTTP se detecta antes de integrarlo.
- Un servicio nuevo queda con un criterio de aceptación uniforme y reproducible.
- Cada `correlation_id` queda verificado en la bitácora real, lo que da evidencia para el requisito de medición de tiempos.

### Negativas

- Cada script levanta contenedores y tarda más que un test unitario. Por eso corre como paso separado de CI, no en cada ejecución local de tests.
- El script duplica parte del código de utilidades (solicitudes HTTP, lectura de bitácora, copia del código) entre servicios. Se decidió no extraerlo a un paquete compartido para mantener cada servicio independiente.
- El requisito puede no aplicar de forma natural a servicios sin API HTTP propia, como `mock-service` o el frontend. Quedan fuera hasta que el equipo lo defina.

## Alternativas consideradas

- **Solo tests unitarios con mocks:** descartado porque no detecta fallas de contenedor, migración ni comunicación entre servicios, que es lo que señaló la revisión del PR #14.
- **Suite de integración única para todo el sistema:** descartada por ahora. Un script por servicio permite que cada uno se pruebe sin depender del estado de los demás y localiza mejor las fallas. Una suite de extremo a extremo puede sumarse en la Etapa III, con la prueba de carga.
- **Extraer las utilidades a un paquete compartido:** descartado para no acoplar los servicios entre sí en esta etapa. Puede revisarse si la duplicación crece.
