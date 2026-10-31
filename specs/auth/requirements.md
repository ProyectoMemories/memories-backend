# Spec: auth — Requisitos

- Módulo: `auth`
- Requisitos: RF-01, RF-03, RF-05, RF-23, RF-24 (Lista de requisitos)
- Reglas vigentes: RN-06, RN-07, RN-08, RN-09, RN-10, RN-11, RN-12, RN-14,
  RN-17, RN-19, RN-50, RN-51, RN-67, RN-68 (05-reglas-de-negocio)
- Decisiones: D22, D28, D41, D56, D60, D62 (01-decisiones)
- Estado: **aprobado**

Fuera de este spec (van en `specs/users/`): ver y editar el perfil (RF-04),
desactivar la cuenta (RF-25), eliminarla (RF-26) y las funciones del
superusuario (RF-15, D28).

---

## HU-01 Registrarse (RF-23, RF-24)

Como persona nueva, quiero crear una cuenta para guardar mis recuerdos.

- **Dado** datos válidos (RN-07: nombre, apellido paterno, nombre de usuario,
  correo, contraseña y fecha de nacimiento; apellido materno opcional),
  **cuando** me registro aceptando la política de privacidad vigente,
  **entonces** se crea la cuenta en estado `unverified` (RN-12), se guarda qué
  versión de la política acepté y cuándo (RN-50) y se envía el correo de
  verificación.
- **Dado** que tengo menos de 14 años según mi fecha de nacimiento, **cuando**
  me registro, **entonces** el registro se rechaza y no se guarda nada (RN-08,
  RN-51).
- **Dado** que no acepto la política de privacidad, **cuando** me registro,
  **entonces** el registro se rechaza (RN-50).
- **Dado** un nombre de usuario que no cumple el formato de RN-10, **cuando** me
  registro, **entonces** se rechaza con un mensaje que dice qué está mal.
- **Dado** un correo o nombre de usuario que ya existe, sin importar mayúsculas
  (RN-09), **cuando** me registro, **entonces** se rechaza.
- **Dado** una contraseña de menos de 8 o más de 64 caracteres, o que está en
  la lista de contraseñas comunes, **cuando** me registro, **entonces** se
  rechaza. No se exigen mayúsculas, números ni símbolos (D62-B).
- **Dado** que envío el campo `is_superuser`, **cuando** me registro,
  **entonces** se ignora o se rechaza: el registro nunca crea superusuarios
  (D28).

## HU-02 Verificar el correo (RF-23, RN-11)

Como persona registrada, quiero confirmar mi correo para poder entrar.

- **Dado** un enlace de verificación con menos de 24 horas, **cuando** lo abro,
  **entonces** la cuenta pasa a `active` y se guarda `email_verified_at`.
- **Dado** un enlace vencido o alterado, **cuando** lo abro, **entonces** se
  rechaza y puedo pedir otro.
- **Dado** que mi cuenta ya está verificada, **cuando** abro el enlace otra vez,
  **entonces** no cambia nada y no hay error.
- **Dado** que mi cuenta sigue sin verificar, **cuando** pido reenviar el
  correo, **entonces** llega un enlace nuevo de 24 horas.
- **Dado** que desde la misma IP ya hubo 5 reenvíos en el último minuto,
  **cuando** pido otro, **entonces** se rechaza (D62-F).

## HU-03 Iniciar sesión (RF-01, RN-06, RN-67)

Como usuario, quiero entrar con mi correo o mi nombre de usuario.

- **Dado** un correo o nombre de usuario (sin importar mayúsculas) y la
  contraseña correcta de una cuenta `active`, **cuando** inicio sesión,
  **entonces** recibo un token de acceso de 15 minutos y un token de renovación
  de 30 días, y se crea una sesión para este dispositivo (RN-67).
- **Dado** credenciales incorrectas, **cuando** inicio sesión, **entonces**
  recibo el mismo error genérico, exista o no la cuenta.
- **Dado** una cuenta `unverified` y la contraseña correcta, **cuando** inicio
  sesión, **entonces** no entro y el mensaje me pide verificar mi correo
  (RN-11). Con la contraseña incorrecta recibo el error genérico (D62-E).
- **Dado** una cuenta `suspended`, **cuando** inicio sesión, **entonces** no
  entro (RN-17).
- **Dado** que desde la misma IP ya hubo 5 intentos en el último minuto,
  **cuando** intento otra vez, **entonces** se rechaza hasta que pase el minuto
  (D62-F).
- **Dado** una cuenta `deactivated`, **cuando** inicio sesión con la contraseña
  correcta, **entonces** la cuenta vuelve a `active` y entro (RN-68).
- **Dado** una cuenta `pending_deletion` dentro de los 30 días, **cuando** inicio
  sesión con la contraseña correcta, **entonces** se cancela la eliminación, la
  cuenta vuelve a `active` y entro (RN-14).

## HU-04 Mantener la sesión (RN-67, D56)

Como usuario, quiero seguir conectado sin escribir mi contraseña cada vez.

- **Dado** un token de renovación vigente, **cuando** lo uso, **entonces**
  recibo un token de acceso nuevo y un token de renovación nuevo; el anterior
  deja de servir y la sesión vence 30 días después de este uso.
- **Dado** un token de renovación que ya se rotó, **cuando** alguien lo usa,
  **entonces** se revoca esa sesión y hay que volver a iniciar sesión.
- **Dado** un token de renovación vencido o de una sesión revocada, **cuando** lo
  uso, **entonces** se rechaza.
- **Dado** que mi cuenta dejó de estar activa (por ejemplo, fue suspendida),
  **cuando** hago cualquier petición, **entonces** se rechaza aunque mi token de
  acceso no haya vencido (RN-67, RN-17).

## HU-05 Cerrar sesión (RF-03, RN-67)

- **Dado** que tengo sesión en este dispositivo, **cuando** cierro sesión,
  **entonces** se revoca solo la sesión de este dispositivo y el cliente borra
  sus tokens.
- **Dado** que cierro sesión dos veces, **cuando** lo hago, **entonces** la
  segunda vez tampoco da error.

## HU-06 Recuperar la contraseña (RF-05, RN-19)

Como usuario que olvidó su contraseña, quiero crear una nueva sin iniciar
sesión.

- **Dado** un correo, **cuando** pido recuperar la contraseña, **entonces** la
  respuesta es la misma exista o no la cuenta, y si existe se envía un enlace.
- **Dado** un enlace con menos de 30 minutos (D62-A) y una contraseña nueva que
  cumple D62-B, **cuando** la envío, **entonces** se guarda, se revocan
  **todas** mis sesiones (RN-67) y el enlace deja de servir (RN-19).
- **Dado** un enlace vencido, alterado o ya usado, **cuando** lo uso,
  **entonces** se rechaza.
- **Dado** que desde la misma IP ya hubo 5 pedidos de recuperación en el último
  minuto, **cuando** pido otro, **entonces** se rechaza (D62-F).

## HU-07 Cambiar la contraseña (RN-67)

- **Dado** que tengo sesión, escribo mi contraseña actual correcta y la nueva
  cumple D62-B, **cuando** la cambio, **entonces** se guarda la nueva y se
  revocan todas mis sesiones.
- **Dado** una contraseña actual incorrecta, **cuando** intento cambiarla,
  **entonces** se rechaza y no se revoca nada.

