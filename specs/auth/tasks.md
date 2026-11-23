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

## Clean Architecture (aprobada el 2026-11-19)

- [x] Mover `auth` y lo común a `entities/`, `use_cases/`, `adapters/` y
      `frameworks/` sin cambiar el comportamiento · tests: las pruebas de la API
      siguen en verde; unitarias nuevas de entidades e interactores con dobles
      en memoria
- [x] `import-linter` en el CI · test: `lint-imports` falla si un círculo
      importa a uno de afuera

## Contraseña

- [x] `User.change_password()` actualiza el hash y `password_changed_at` ·
      test de entidad
- [x] Puertos `PasswordResetTokens` y `SessionGateway.revoke_all` con sus
      adaptadores · tests: token vencido, alterado y con otra fecha se rechaza;
      revoke_all cierra solo las sesiones abiertas de esa cuenta
- [x] `POST /auth/password/forgot` · tests: misma respuesta exista o no la
      cuenta, suspendida no recibe correo, sexto pedido en un minuto → 429
- [x] `POST /auth/password/reset` · tests: guarda la contraseña, revoca todas
      las sesiones (Android y web), el enlace usado ya no sirve, vencido y
      alterado se rechazan, contraseña común se rechaza
- [x] `POST /auth/password/change` · tests: actual incorrecta → 422 y no revoca
      nada; correcta revoca todas (también la propia); sin token → 401; sexto
      intento en un minuto → 429

## Correos después de responder (D74)

- [x] `DeferredEmailSender` guarda los correos y los envía con `flush()` ·
      tests: `send` no envía; `flush` envía en orden y vacía la lista; si uno
      falla, se registra sin el contenido y sigue con el siguiente
- [x] `forgot` y `resend` usan el enviador diferido; `register`, el directo ·
      tests: la respuesta HTTP sale antes que el correo en `forgot` y
      `resend`; con el SMTP caído siguen respondiendo 202

## Límite de intentos en Redis (D77)

- [x] Contrato `RateLimit` y `InMemoryRateLimiter` (renombre, mismo
      comportamiento) · tests: los de siempre; una `X-Forwarded-For` inventada
      no cambia la IP con que se cuenta
- [x] `RedisRateLimiter` con transacción `INCR`/`EXPIRE NX`/`TTL` y vuelta a
      memoria · tests contra Redis real: sexto intento rechazado con espera
      entre 1 y 60 s; claves separadas; la clave siempre tiene vencimiento;
      con Redis inalcanzable cuenta en memoria y registra el aviso
- [x] `REDIS_URL` en la configuración y elección en `create_app` · tests: con
      URL usa Redis, sin URL usa memoria
- [ ] Servicio `redis` en Docker Compose y el CI, `.env.example`, README y
      CLAUDE.md · test: el CI levanta Redis y la API sana con él

## Correcciones

- [x] El token de acceso deja de servir al cerrar la sesión (se revisa la
      sesión del `sid` en cada petición) · tests: tras el logout (Android y
      web) el token de acceso da 401; con la sesión vencida o de otra cuenta,
      también
