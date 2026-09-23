# Spec: cuentas y sesiones — Requisitos

- Capacidad del PRD: soporte de CP-06 (privacidad por defecto)
- Estado: implementado

## Contexto

Memories es privado por defecto: cada persona ve solo sus recuerdos. Para que eso
signifique algo hace falta saber quien es quien. Esta feature no aporta valor
visible por si sola; es la condicion para que el resto lo tenga.

## Historias de usuario

### HU-01 — Crear una cuenta

> Como persona que quiere guardar recuerdos, quiero crear una cuenta con mi
> correo y una contrasena, para que mis recuerdos sean mios.

**Criterios de aceptacion**

- Dado un correo libre y una contrasena de 8 caracteres o mas,
  cuando me registro,
  entonces se crea mi cuenta con rol `user` y recibo mis datos **sin** la
  contrasena ni su hash.
- Dado un correo que ya tiene cuenta,
  cuando me registro,
  entonces recibo 409 con el codigo `email_already_registered`.
- Dado el correo `Victor@Memories.App`,
  cuando me registro,
  entonces se guarda como `victor@memories.app` (no se pueden crear dos cuentas
  que solo difieren en mayusculas).
- Dada una contrasena de menos de 8 caracteres,
  cuando me registro,
  entonces recibo 422 y la cuenta no se crea.

### HU-02 — Iniciar sesion

> Como persona registrada, quiero iniciar sesion, para volver a mis recuerdos
> desde cualquier dispositivo.

**Criterios de aceptacion**

- Dadas credenciales correctas, cuando inicio sesion, entonces recibo un token de
  acceso, uno de refresco y mi perfil.
- Dada una contrasena incorrecta **o** un correo que no existe, cuando inicio
  sesion, entonces recibo 401 **con el mismo mensaje en ambos casos** (no se
  revela si esa cuenta existe).
- Dada una cuenta desactivada, cuando inicio sesion, entonces recibo 401.
- Dados mas de 10 intentos en un minuto desde la misma IP, cuando vuelvo a
  intentarlo, entonces recibo 429.

### HU-03 — Seguir dentro sin volver a escribir la contrasena

> Como persona que usa la app a diario, quiero que la sesion se renueve sola,
> para no escribir la contrasena cada media hora.

**Criterios de aceptacion**

- Dado un token de refresco valido, cuando lo uso, entonces recibo un par nuevo
  **y el anterior deja de valer** (rotacion).
- Dado un token de refresco ya usado o revocado, cuando lo uso, entonces recibo
  401.

### HU-04 — Cerrar sesion

> Como persona que comparte o pierde un dispositivo, quiero cerrar sesion, para
> que nadie siga entrando con mi cuenta.

**Criterios de aceptacion**

- Dada una sesion abierta, cuando cierro sesion, entonces el token de refresco
  deja de valer.
- Dado un token de refresco que ya no vale, cuando cierro sesion otra vez,
  entonces la respuesta sigue siendo correcta (es idempotente).

### HU-05 — Ver y cambiar mi perfil

- Dado que estoy autenticado, cuando pido `/users/me`, entonces recibo mi perfil.
- Dado que no envio token, cuando pido `/users/me`, entonces recibo 401.
- Dado el rol `user`, cuando pido la lista de usuarios, entonces recibo 403.

## Fuera de esta feature

Recuperacion de contrasena por correo, verificacion de correo, inicio de sesion
con Google o Apple, y sesion unica por dispositivo. Ninguna esta en el MVP.

## Riesgo aceptado

El tiempo de respuesta del login permite, en teoria, distinguir un correo
registrado de uno que no lo esta (con un correo inexistente no se verifica ningun
hash). Se asume en esta fase; si el producto sale del circulo del equipo, se
mitiga verificando siempre contra un hash ficticio.
