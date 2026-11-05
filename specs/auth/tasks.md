# Spec: auth — Tareas

Depende de `chore/docker-compose` (con Mailpit), `feat/app-skeleton` y
`feat/db-initial-migration`.

Cada tarea lleva su test. Se marcan `[x]` al terminar.

## Base

- [x] Modelos SQLAlchemy de `app_user` y `privacy_consent` (alineados con la
      migración 0001)
- [x] Modelo SQLAlchemy de `user_session`
- [x] Hash de contraseñas con pwdlib y Argon2 detrás de una interfaz · test:
      verifica, rechaza y recalcula hashes con parámetros viejos
- [x] Validación de contraseña (8 a 64, lista de comunes) · tests: límites y
      una contraseña común
- [x] Emisión y validación del JWT de acceso (15 min, `sub`, `sid`,
      `type: "access"`) · tests: vencido, alterado y sin `type` se rechazan;
      un enlace de verificación no sirve como token de acceso
- [x] Tokens firmados de correo con propósito · test: uno de verificación no
      sirve para recuperar

## Registro y verificación

- [x] `POST /auth/register` · tests: datos válidos, menor de 14, sin
      consentimiento, usuario y correo repetidos sin importar mayúsculas,
      formato de usuario inválido, `is_superuser` rechazado
- [x] Interfaz `send_email`: SMTP hacia Mailpit en desarrollo y enviador
      falso en tests
- [x] `POST /auth/verify-email` y `/resend` · tests: vigente, vencido,
      alterado, ya verificado

## Sesión

- [x] Límite de 5 intentos por minuto por IP, en memoria · test: el sexto
      intento se rechaza y pasa al minuto siguiente
- [x] Límite de intentos también en `POST /auth/register` · test: el sexto
      registro en un minuto se rechaza
- [x] `POST /auth/login` (Android y web) · tests: correo y usuario, error
      genérico, `unverified` con contraseña correcta e incorrecta (D62-E),
      `suspended`, `deactivated` se reactiva,
      `pending_deletion` se cancela
- [x] Dependencia "usuario actual" que exige cuenta activa · test: un usuario
      suspendido con JWT vigente es rechazado
- [x] `POST /auth/refresh` · tests: rota, vencido, revocado, **reuso revoca la
      sesión**
- [x] Cookie y revisión de `Origin` en web · tests: origen distinto rechazado,
      cookie con sus atributos
- [x] `POST /auth/logout` · tests: revoca solo esa sesión, es idempotente

## Contraseña

- [ ] `POST /auth/password/forgot` y `/reset` · tests: respuesta igual exista o
      no la cuenta, revoca todas las sesiones, enlace usado ya no sirve
- [ ] `POST /auth/password/change` · tests: actual incorrecta no revoca nada;
      correcta revoca todas
