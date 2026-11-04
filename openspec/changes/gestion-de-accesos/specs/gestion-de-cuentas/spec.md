# Spec Delta

## Purpose

Esta capacidad define los roles de la plataforma y el ciclo de habilitación de organizadores, para que cada persona pueda acceder únicamente a las funciones correspondientes a su rol y estado.

## ADDED Requirements

### Requirement: Roles y capacidades de usuario
El sistema DEBE (MUST) distinguir los roles de administrador, organizador y cliente, y limitar las funciones disponibles según el rol y el estado de la cuenta.

#### Scenario: Administrador gestiona la plataforma
- **WHEN** un administrador autenticado accede a la plataforma
- **THEN** puede realizar las tareas de gestión, mantenimiento y operación administrativa

#### Scenario: Organizador habilitado gestiona eventos
- **WHEN** un organizador habilitado accede a la plataforma
- **THEN** puede diseñar y publicar sus eventos

#### Scenario: Cliente accede a funciones de compra
- **WHEN** un cliente autenticado accede a la plataforma
- **THEN** puede utilizar las funciones de compra de entradas para eventos listados

### Requirement: Roles simultáneos con estados independientes
El sistema DEBE (MUST) permitir que una misma cuenta tenga los roles de cliente y organizador. El estado del rol de organizador no DEBE (MUST NOT) deshabilitar las funciones del rol de cliente cuando este permanezca activo.

#### Scenario: Cliente solicita el rol de organizador
- **WHEN** un cliente existente se registra como organizador
- **THEN** el sistema agrega a la misma cuenta el rol de organizador en estado Pendiente de habilitación y conserva activo el rol de cliente

#### Scenario: Organizador solicita el rol de cliente
- **WHEN** un organizador existente se registra como cliente
- **THEN** el sistema agrega el rol de cliente a la misma cuenta y conserva sin cambios el estado del rol de organizador

#### Scenario: Rol de organizador pendiente o deshabilitado
- **WHEN** una cuenta tiene activo el rol de cliente y el rol de organizador está Pendiente de habilitación o Deshabilitado
- **THEN** el sistema permite las funciones de cliente y bloquea las funciones de organizador

### Requirement: Registro propio de organizadores
El sistema DEBE (MUST) permitir que una persona se registre como organizador con email y contraseña y asignar a su cuenta el rol de organizador en estado Pendiente de habilitación hasta que un administrador lo habilite.

#### Scenario: Registro de un nuevo organizador
- **WHEN** una persona completa el registro como organizador con email y contraseña
- **THEN** el sistema crea o utiliza la cuenta de esa persona, asigna el rol de organizador en estado Pendiente de habilitación y no otorga permisos de organizador

#### Scenario: Registro sin verificación de email
- **WHEN** una persona completa el registro como organizador sin verificar su email
- **THEN** el sistema mantiene la cuenta en estado Pendiente de habilitación sin exigir verificación de email en el alcance inicial

### Requirement: Registro propio de clientes
El sistema DEBE (MUST) permitir que una persona se registre como cliente con email y contraseña, y habilitar su cuenta para comprar entradas sin exigir verificación de email en el alcance inicial.

#### Scenario: Cliente se registra sin verificar su email
- **WHEN** una persona completa el registro como cliente con email y contraseña, sin verificar su email
- **THEN** el sistema crea la cuenta habilitada y permite que inicie sesión y compre entradas para eventos listados

### Requirement: Inicio de sesión de clientes
El sistema DEBE (MUST) permitir que un cliente activo inicie sesión con el email y la contraseña asociados a su cuenta.

#### Scenario: Cliente ingresa credenciales válidas
- **WHEN** un cliente activo inicia sesión con el email y la contraseña correctos
- **THEN** el sistema autentica al cliente y le habilita las funciones de compra correspondientes a su rol

#### Scenario: Cliente ingresa credenciales incorrectas
- **WHEN** una persona intenta iniciar sesión con credenciales que no coinciden con una cuenta activa
- **THEN** el sistema rechaza el inicio de sesión

### Requirement: Acceso limitado de organizador pendiente
El sistema DEBE (MUST) permitir que un organizador pendiente inicie sesión con el email y la contraseña de su cuenta para consultar el estado de habilitación, pero DEBE (MUST) impedirle acceder a las funciones de organizador.

#### Scenario: Organizador pendiente consulta su estado
- **WHEN** un organizador Pendiente de habilitación inicia sesión con sus credenciales
- **THEN** el sistema le informa que su cuenta espera habilitación administrativa y no le permite diseñar ni publicar eventos

### Requirement: Habilitación administrativa de organizadores
El sistema DEBE (MUST) permitir que un administrador habilite a un organizador pendiente o reactive a un organizador deshabilitado; una vez habilitado, el organizador puede usar sus funciones sin aprobación administrativa individual por evento.

#### Scenario: Administrador habilita una cuenta
- **WHEN** un administrador habilita a un organizador Pendiente de habilitación
- **THEN** el sistema cambia la cuenta a Habilitada y concede las funciones de organizador

#### Scenario: Administrador reactiva una cuenta deshabilitada
- **WHEN** un administrador reactiva a un organizador Deshabilitado
- **THEN** el sistema cambia la cuenta a Habilitada y permite que el organizador vuelva a iniciar sesión y usar sus funciones

#### Scenario: Organizador habilitado publica un evento
- **WHEN** un organizador Habilitado publica un evento que cumple las reglas de publicación
- **THEN** el evento se publica sin requerir una aprobación administrativa adicional

#### Scenario: Organizador habilitado inicia sesión
- **WHEN** un organizador Habilitado inicia sesión con su email y contraseña
- **THEN** el sistema le permite acceder a las funciones de gestión de sus eventos

### Requirement: Desactivación de organizadores
El sistema DEBE (MUST) permitir que un administrador desactive el rol de organizador, bloquear sus funciones y permitir pausar o despublicar sus eventos existentes, sin deshabilitar otros roles activos de la misma cuenta.

#### Scenario: Organizador desactivado intenta iniciar sesión
- **WHEN** un organizador Deshabilitado intenta iniciar sesión
- **THEN** el sistema impide el acceso a las funciones de organizador y permite iniciar sesión solo si la cuenta conserva otro rol activo

#### Scenario: Administrador pausa o despublica un evento
- **WHEN** un administrador pausa o despublica un evento de un organizador desactivado
- **THEN** el evento deja de estar disponible para nuevas compras según la acción aplicada
