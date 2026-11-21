# ADR-0009: Sesión web con Identity

- Estado: Aceptado
- Fecha: 2026-11-19

## Contexto

La aplicación web necesita mantener sesiones sin guardar una credencial de renovación accesible a JavaScript. Identity ya ofrece tokens de acceso y renovación rotativa en JSON para clientes API. El diseño de `gestion-de-accesos` reservó una integración web con cookie, protección CSRF y coordinación entre pestañas.

## Decisión

Se adopta una interfaz web de sesión en Identity que entregue la credencial de renovación mediante una cookie HttpOnly, sin atributo Domain, y mantenga el JWT de acceso en memoria del cliente. La cookie será Secure en HTTPS y SameSite=Strict cuando frontend e Identity compartan sitio. La excepción para HTTP local será explícita y no aplicará a otros entornos.

Las operaciones web de renovación y cierre serán POST y validarán un token CSRF asociado a la sesión y el origen configurado. Si frontend e Identity utilizan orígenes distintos, CORS admitirá solo orígenes explícitos y credenciales. El cliente coordinará renovaciones y cierre entre pestañas para evitar el uso simultáneo de la misma credencial rotativa. Una respuesta de renovación perdida podrá requerir un nuevo inicio de sesión.

Cada instancia de Identity admitirá un único origen de frontend para sesiones web, que puede ser distinto del origen de Identity. Web Locks y BroadcastChannel se limitan al origen, mientras las cookies pueden compartirse entre puertos del mismo host; permitir varios orígenes de frontend sin aislar las cookies impediría garantizar la coordinación. Identity rechazará una configuración con más de un origen de frontend.

La adaptación web mantiene los formatos JSON existentes para clientes API. La integración de servicios consumidores seguirá el ADR-0004 y la revocación posterior documentada en el [ADR-0011](0011-revocacion-inmediata-sesiones.md); la protección del canal y la distribución de claves entre servicios se tratan por separado.

## Consecuencias

### Positivas

- La credencial de renovación no queda accesible desde JavaScript ni se persiste en almacenamiento web.
- Las sesiones web pueden restaurarse al recargar sin ampliar el límite absoluto de sesión existente.
- El contrato actual de clientes API puede seguir funcionando.

### Negativas

- Identity y el cliente web deben coordinar cookies, CSRF, orígenes y concurrencia entre pestañas.
- Los despliegues locales HTTP y las combinaciones de origen/sitio requieren pruebas específicas en navegador.
- Las respuestas perdidas y los conflictos entre pestañas pueden obligar a reautenticarse.
- Varios orígenes de frontend simultáneos requieren rediseñar el aislamiento de sesión antes de habilitarse.

## Alternativas consideradas

- Guardar el refresh token en almacenamiento web: se descarta porque JavaScript puede leerlo y persistirlo.
- Mantener solo el JWT en memoria sin restauración: reduce componentes, pero pierde la sesión al recargar y no cubre la renovación prevista.
- Reemplazar el contrato JSON actual: se descarta para evitar romper clientes API existentes.
