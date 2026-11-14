# ADR-0004: Autenticación entre servicios con JWT firmados

- Estado: Propuesto
- Fecha: 2026-11-13

## Contexto

Identity debe acreditar la identidad de una persona ante los servicios de Eventos y Compras. Los permisos de organizador pueden cambiar durante una sesión, por lo que una credencial emitida previamente no debe considerarse una fuente suficiente del estado actual de ese rol.

## Decisión

Identity emitirá JWT de acceso firmados con RS256 y una clave privada, con vigencia máxima de una hora y sin superar las 24 horas desde el inicio de sesión. La renovación utiliza una credencial separada y rotativa; reutilizar una credencial ya consumida revoca la sesión. La clave privada es exclusiva de Identity. Los servicios consumidores verificarán con una clave pública confiable la firma, el algoritmo esperado, el vencimiento, el emisor y la audiencia previstos.

Para acciones protegidas por rol, los consumidores consultarán a Identity el estado actual de la cuenta y sus roles mediante una interfaz interna por identificador de cuenta. Cada servicio se autenticará con una credencial propia y separada; si no se puede verificar el estado, se rechazará la operación protegida. Eventos verificará además la propiedad del evento, y Compras asociará compras y consultas al identificador de la persona autenticada.

Las credenciales no incluirán contraseñas. Los secretos y claves reales se suministrarán fuera del repositorio. Para desarrollo local se permiten credenciales de demostración reemplazables y generación persistente de claves; solo Identity recibe la clave privada. Antes de integrar los servicios, el equipo debe acordar los detalles del contrato, la protección del canal, la distribución confiable de la clave pública y los procedimientos de rotación y revocación.

Cerrar una sesión revoca su credencial de renovación, pero no invalida inmediatamente un JWT ya emitido y verificado localmente: este puede seguir siendo válido hasta su vencimiento. Los roles se consultan de nuevo para las acciones protegidas.

## Consecuencias

### Positivas

- Los consumidores pueden comprobar la autenticidad del token sin compartir la clave privada.
- Los permisos vigentes se consultan a su dueño y no dependen solo de datos emitidos durante el inicio de sesión.

### Negativas

- Las acciones protegidas dependen de la disponibilidad de Identity para consultar roles.
- Es necesario gestionar claves, distribución confiable y rotación entre servicios.
- La verificación local no ofrece revocación inmediata de JWT ya emitidos.

## Alternativas consideradas

- **Consultar Identity para validar cada credencial opaca:** centraliza la validación, pero incorpora una llamada remota para cada verificación del token.
- **Confiar únicamente en roles incluidos en el JWT:** se descarta porque podría conservar permisos de organizador después de deshabilitarlo hasta el vencimiento del token.
- **Firma simétrica compartida:** exige compartir un secreto capaz de firmar entre consumidores; se prefiere que únicamente Identity posea la clave de firma.
