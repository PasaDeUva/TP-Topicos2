# ADR-0011: Revocación inmediata de sesiones

- Estado: Aceptado
- Fecha: 2026-11-21

## Contexto

El ADR-0004 aceptado permite verificar JWT localmente hasta su vencimiento después del cierre. Se requiere impedir nuevas autorizaciones en Identity desde que la sesión se revoca y preparar una verificación para futuros consumidores.

## Decisión

Los nuevos JWT incluirán un identificador firmado de sesión. Identity comprobará la firma, la cuenta, la pertenencia de la sesión y su vigencia y revocación consultando el estado persistido. Se rechazarán tokens anteriores sin identificador de sesión. Los consumidores futuros deberán verificar el token completo y el estado de sesión con Identity para cada nueva autorización protegida, además de consultar roles cuando corresponda; si no pueden verificar, rechazarán la operación. Las operaciones ya autorizadas pueden finalizar.

Esta decisión reemplaza el límite de revocación posterior al cierre establecido en [ADR-0004](0004-autenticacion-entre-servicios.md); no implementa la integración de Eventos o Compras. Se mantienen las demás obligaciones de firma, verificación y consulta de roles.

## Consecuencias

### Positivas

- Los tokens de una sesión revocada no autorizan nuevas solicitudes protegidas en Identity.
- Las sesiones independientes de una cuenta conservan su propio estado.

### Negativas

- La autorización inmediata depende de la disponibilidad y carga de Identity y su base de sesiones.
- Los JWT anteriores sin identificador de sesión dejan de ser aceptados; sus titulares necesitan renovar o volver a iniciar sesión.
- Revertir el cambio restaura la ventana de uso de tokens hasta su vencimiento.

## Alternativas consideradas

- Validar únicamente firma y vencimiento localmente: conserva disponibilidad, pero no ofrece revocación inmediata.
- Mantener una caché del estado activo: reduce consultas, pero una entrada obsoleta puede autorizar después de la revocación.
- Aceptar temporalmente tokens anteriores: evita interrupciones, pero mantiene una ventana sin revocación inmediata.
