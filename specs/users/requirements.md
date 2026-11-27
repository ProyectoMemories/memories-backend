# Spec: users — Requisitos

- Módulo: `users`
- Requisitos: RF-04 (ver el perfil; Lista de requisitos)
- Reglas vigentes: RN-07 (datos del perfil), RN-08 (edad mínima)
- Decisiones: D13, D60, D69, D78 (01-decisiones). Por registrar en el 01:
  "D81" (el módulo `users` es dueño de los datos del perfil) y "D82"
  (`GET /users/me` se adelanta a F7 del frontend). Ver design §1.
- Regla por registrar en el 05: la fecha de nacimiento no se cambia después
  del registro (design §1).
- Estado: **borrador**, para revisar

Alcance de esta primera entrega: solo **leer el perfil propio**, para que la
app muestre el nombre en Inicio y en Perfil. Editar el perfil (RF-04),
desactivar la cuenta (RF-25), eliminarla (RF-26) y las funciones del
superusuario (RF-15) llegan después, en esta misma spec.

---

## HU-01 Ver mi perfil (RF-04)

Como persona con sesión iniciada, quiero ver mis datos para saber con qué
cuenta entré.

- **Dado** que inicié sesión, **cuando** pido mi perfil, **entonces** recibo
  mi nombre, apellido paterno, apellido materno (o vacío si no lo puse),
  nombre de usuario y correo.
- **Dado** que no envío token, o envío uno vencido, de otra firma o de una
  sesión cerrada, **cuando** pido mi perfil, **entonces** recibo 401 con
  `not_authenticated` o `access_token_expired`, igual que en el resto de la
  API (D56).
- **Dado** dos cuentas, **cuando** cada una pide su perfil, **entonces** cada
  una recibe solo sus propios datos: no hay forma de pedir el perfil de otra
  cuenta por este endpoint (RNF-02).
- **Dado** que pido mi perfil, **cuando** responde, **entonces** no incluye la
  fecha de nacimiento, el hash de la contraseña, el estado de la cuenta ni si
  es superusuario: la app no los necesita para mostrar el nombre (privacidad
  por defecto).

## Reglas para las entregas siguientes (no se implementan ahora)

- **Fecha de nacimiento fija** (**[PROPUESTA]** aprobada por Victor el
  2026-11-27, falta registrarla en el 05): después del registro la fecha de
  nacimiento no se puede cambiar desde la app. El endpoint para editar el
  perfil no la acepta. Evita que alguien mienta sobre su edad para saltarse
  RN-08. La app ya lo avisa en el registro.
