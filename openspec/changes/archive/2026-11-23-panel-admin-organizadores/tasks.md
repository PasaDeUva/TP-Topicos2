# Tasks

## 1. Consulta y seguridad en Identity

- [x] 1.1 Agregar la consulta administrativa de organizadores con orden estable y datos mínimos; verificar estados, lista vacía y ausencia de credenciales mediante pruebas de API.
- [x] 1.2 Verificar con pruebas que la consulta rechaza sesiones ausentes o inválidas y usuarios sin rol administrador activo, incluyendo revocación del rol.
- [x] 1.3 Permitir PATCH desde los orígenes configurados y probar preflight autorizado y origen rechazado sin modificar la protección de sesión web.
- [x] 1.4 Documentar el nuevo contrato y comprobar que las pruebas de los endpoints existentes y sus códigos siguen pasando.

## 2. Panel web de administración

- [x] 2.1 Integrar consulta y cambio de estado con el token en memoria; probar peticiones, errores 401/403 y respuestas tardías ante cambio de sesión.
- [x] 2.2 Crear la vista administrativa para estados pendientes, habilitados y deshabilitados; probar visibilidad por rol, lista vacía, carga, error y reintento.
- [x] 2.3 Incorporar habilitación y deshabilitación con progreso y reconciliación de resultados inciertos; probar éxito, error y preservación de otros roles.
- [x] 2.4 Adaptar la vista para mobile y teclado, documentar su uso y ejecutar pruebas de interfaz, lint y build.

## 3. Integración

- [x] 3.1 Ejecutar la suite backend y frontend y verificar el flujo web completo con administrador y no administrador en datos aislados.
- [x] 3.2 Verificar despliegue y reversión en el orden documentado sin recrear servicios ni modificar datos o secretos ajenos sin autorización.
