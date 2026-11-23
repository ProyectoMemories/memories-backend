# Spec: auth — Diseño

Estado: **aprobado**. Los puntos marcados [PROPUESTA] no están decididos en
Drive; se pueden ajustar al implementar, avisando en el PR.

## 1. Tablas (memories-physical-v1.5.sql)

| Tabla | Uso |
|---|---|
| `app_user` | Cuenta. `status` (`account_status`), `email_verified_at`, `password_changed_at`, `deletion_requested_at`, `is_superuser`. |
| `privacy_consent` | Una fila por versión de política aceptada (RN-50). |
| `user_session` | Una fila por dispositivo con sesión: `refresh_token_hash`, `platform` (`android` o `web`), `device_name`, `expires_at`, `last_used_at`, `revoked_at`. |

No hay tablas para tokens de verificación ni de recuperación: son **tokens
firmados** de vida corta (RN-19), igual que en el modelo físico.

## 2. Endpoints

[PROPUESTA] Prefijo `/api/v1` y nombres en inglés. Errores con un cuerpo común
`{ "code": "...", "message": "..." }`.

| Método y ruta | Qué hace | HU |
|---|---|---|
| `POST /auth/register` | Crea la cuenta `unverified`, guarda el consentimiento y envía el correo | HU-01 |
| `POST /auth/verify-email` | Recibe el token del enlace y activa la cuenta | HU-02 |
| `POST /auth/verify-email/resend` | Reenvía el enlace; responde igual exista o no la cuenta | HU-02 |
| `POST /auth/login` | Credenciales → tokens + sesión nueva | HU-03 |
| `POST /auth/refresh` | Rota el token de renovación | HU-04 |
| `POST /auth/logout` | Revoca la sesión actual | HU-05 |
| `POST /auth/password/forgot` | Envía el enlace de recuperación | HU-06 |
| `POST /auth/password/reset` | Token + contraseña nueva; revoca todas las sesiones | HU-06 |
| `POST /auth/password/change` | Contraseña actual + nueva; revoca todas las sesiones | HU-07 |

### Registro y verificación (D65)

- El cliente manda `accepts_privacy_policy: true`; la API guarda la versión
  vigente, que viene de la variable `PRIVACY_POLICY_VERSION` (RN-50, D65).
- Un campo desconocido, como `is_superuser`, responde 422 (D28, D65).
- SQLAlchemy síncrono (D65).
- Respuestas: `register` 201 con `id`, `username`, `email` y `status`;
  `verify-email` 204; `resend` 202 sin cuerpo.
- Códigos de error: `username_taken` y `email_taken` (409); `underage`,
  `privacy_policy_not_accepted`, `password_length`, `password_too_common` y
  `validation_error` (422); `expired_token` e `invalid_token` (400);
  `too_many_requests` (429, con `Retry-After`).
- El enlace del correo abre la app web en `/verify-email?token=...`; esa
  pantalla llama a `verify-email` (D65). El enlace que abre la app en Android
  se define con el frontend.
- Si el correo no se puede enviar, la cuenta queda creada y se registra el
  error (sin el enlace); la persona puede pedir otro.

### Login, refresh y logout

- `login` recibe `identifier` (correo o nombre de usuario), `password`,
  `platform` (`android` o `web`) y `device_name` opcional. Responde 200 con
  `access_token`, `token_type: "bearer"` y `expires_in` (segundos); en
  Android, además, `refresh_token`.
- `refresh` en Android recibe `{"refresh_token": "..."}`; en web no lleva
  cuerpo y usa la cookie. Responde igual que `login`.
- `logout` responde 204 siempre (idempotente); en web, además, borra la
  cookie.
- El canal debe coincidir con la plataforma de la sesión: un token de una
  sesión `web` no sirve en el cuerpo, ni uno de `android` en la cookie.
- Códigos: `invalid_credentials` (401, genérico), `email_not_verified` y
  `account_suspended` (403, solo con la contraseña correcta, D62-E),
  `invalid_refresh_token` (401), `origin_not_allowed` (403),
  `not_authenticated` y `access_token_expired` (401, con
  `WWW-Authenticate: Bearer`). La app renueva el token solo con
  `access_token_expired`.
- Para no revelar si la cuenta existe por el tiempo de respuesta, un login con
  un usuario inexistente igual calcula un hash.

### Recuperar y cambiar la contraseña (HU-06, HU-07)

[PROPUESTA aprobada por el equipo el 2026-11-19, pendiente de registrar en el
01]

- `password/forgot` recibe `{"email"}` y responde **202 siempre**. Si la cuenta
  existe y no está suspendida, envía un enlace a `/reset-password?token=...` de
  la app web (igual que D65). Una cuenta suspendida no recibe nada: igual no
  puede entrar (RN-17). Recuperar la contraseña no cambia el estado de la
  cuenta.
- `password/reset` recibe `{"token", "new_password"}` y responde **204**.
- `password/change` exige el token de acceso, recibe
  `{"current_password", "new_password"}` y responde **204**. Con la actual
  incorrecta responde **422 `current_password_incorrect`**, no 401: la app
  trata un 401 como un problema de sesión.
- Los dos guardan la contraseña nueva (D62-B), actualizan
  `password_changed_at` y revocan **todas** las sesiones, también la de quien
  hizo el cambio (RN-67): la app debe volver al login.
- **Enlace de un solo uso sin tabla (RN-19):** el token lleva
  `password_changed_at` del momento en que se pidió. Si al usarlo ya no
  coincide (porque se usó o porque la contraseña cambió por otro camino), se
  rechaza con `invalid_token`.
- **Límite de intentos (D62-F):** 5 por minuto por IP en `password/forgot` y
  también en `password/change`, para que un token robado no sirva para probar
  contraseñas.

### Cómo viaja el token de renovación (D56)

- **Android:** en el cuerpo de la respuesta de `login` y `refresh`; el cliente
  lo guarda en el almacenamiento seguro y lo manda en el cuerpo de `refresh` y
  `logout`.
- **Web:** en la cookie `memories_refresh`, `HttpOnly`, `Secure`,
  `SameSite=Strict`, con `Path` limitado a `/api/v1/auth` y vida de 30 días. No
  aparece en el cuerpo de la respuesta.
- La plataforma la declara el cliente al iniciar sesión (`platform`, más un
  `device_name` opcional) y queda guardada en la sesión.

### Protección CSRF en web

- `refresh` y `logout` en web revisan la cabecera `Origin` y la comparan con el
  dominio de la app web (variable de entorno). Si no coincide, se rechaza.
- CORS solo permite ese dominio, con credenciales. Nunca `*`.
- [PROPUESTA] `SameSite=Strict`: en local la API (`localhost:8001`) y la app
  web (`localhost:3000`) son el mismo sitio (el puerto no cuenta). Si al
  desplegar quedan en sitios distintos, se revisa junto con los dominios.
- Sin cabecera `Origin`, o con otro origen, `refresh` y `logout` por cookie
  responden 403 `origin_not_allowed`.

## 3. Reglas de sesión (D56, RN-67)

- **Token de acceso:** JWT de 15 minutos con `sub` (id de usuario), `sid`
  (id de sesión) y `type: "access"`. No se guarda. Usa la misma `SECRET_KEY`
  que los tokens del correo, así que la API rechaza todo token sin
  `type: "access"`: un enlace de verificación nunca sirve como token de
  acceso. Y al revés, un token de acceso no sirve como enlace, porque no lleva
  `purpose`.
- **En cada petición** con token de acceso se revisa que la cuenta siga activa
  **y que la sesión de su `sid` siga abierta** (sin revocar y sin vencer). Así,
  cerrar sesión o cambiar la contraseña corta también el token de acceso al
  instante, y un token robado se puede cortar (D56). Cuesta una lectura por
  clave primaria más por petición.
- **Token de renovación:** `<id de sesión>.<secreto aleatorio>`. Se guarda solo
  el hash del secreto.
- **Rotación:** en cada `refresh` se genera un secreto nuevo, se reemplaza el
  hash, se actualiza `last_used_at` y `expires_at = now() + 30 días`.
- **Reuso:** si el id de sesión existe y no está revocada, pero el hash no
  coincide, el token es viejo → se revoca la sesión y se rechaza la petición.
- **Vencida o revocada:** se rechaza sin cambiar nada.
- **En cada petición autenticada** se lee la cuenta y se exige `status =
  'active'`; si no, se rechaza aunque el JWT siga vigente.
- **Cambio o recuperación de contraseña:** se actualiza `password_changed_at` y
  se revocan todas las sesiones del usuario en la misma transacción.

[PROPUESTA] El hash del secreto del token de renovación es SHA-256. Como el
secreto es aleatorio y largo, no necesita un hash lento como las contraseñas.

## 4. Tokens firmados de correo

| Token | Contenido | Vida | Deja de servir |
|---|---|---|---|
| Verificación | id de usuario, propósito `verify_email` | 24 h (RN-11) | al vencer; verificar dos veces no cambia nada |
| Recuperación | id de usuario, propósito `reset_password`, `password_changed_at` | 30 min (D62-A) | al vencer o cuando cambia `password_changed_at` (RN-19) |

Cada token lleva su propósito, para que uno de verificación no sirva para
recuperar la contraseña.

## 5. Capas (Clean Architecture, CLAUDE.md §5 y §7)

```
app/modules/auth/
├── entities/                  Enterprise Business Rules
│   ├── user.py                User y AccountStatus: verificar, permitir login, reactivar
│   ├── user_session.py        UserSession y ClientPlatform: abrir, rotar, revocar
│   ├── privacy_consent.py     PrivacyConsent (RN-50)
│   ├── age_policy.py          edad mínima (RN-08)
│   ├── password_policy.py     8 a 64 caracteres y contraseñas comunes (D62-B)
│   └── errors.py              errores de negocio
├── use_cases/                 Application Business Rules
│   ├── ports.py               UserGateway, SessionGateway, PasswordHasher,
│   │                          AccessTokens, EmailLinkTokens,
│   │                          PasswordResetTokens, RefreshSecrets
│   ├── errors.py              credenciales, enlaces y sesiones inválidas
│   ├── register_user.py · verify_email.py · resend_verification.py
│   ├── log_in.py · refresh_session.py · log_out.py · authenticate.py
│   ├── request_password_reset.py · reset_password.py · change_password.py
│   ├── refresh_token.py       formato "<id de sesión>.<secreto>"
│   ├── token_issuer.py        arma el JWT de acceso y el token de renovación
│   ├── verification_mailer.py correo con el enlace de verificación
│   └── password_reset_mailer.py correo con el enlace de recuperación
├── adapters/                  Interface Adapters
│   ├── controllers/           routers FastAPI, CurrentUser, cookie y Origin (CSRF)
│   ├── presenters/            esquemas Pydantic y tokens → respuesta (cuerpo o cookie)
│   ├── gateways/              modelos ORM y gateways SQLAlchemy de las tres tablas
│   └── services/              Argon2 (pwdlib), JWT (PyJWT), secretos de renovación
└── frameworks/
    ├── composition.py         crea una vez los adaptadores sin estado (AuthModule)
    └── use_case_factory.py    arma los interactores de cada petición
```

- La edad mínima (RN-08) se valida en `entities/age_policy.py`, no en la base (el `.sql` lo
  deja fuera a propósito: la edad cambia con el tiempo).
- El formato del nombre de usuario se valida en el schema **y** lo impone la
  base (`ck_app_user_username_format`).
- Contraseñas con **pwdlib y Argon2** (D62-D, cierra P22), detrás de una
  interfaz pequeña para poder cambiar el algoritmo (RNF-08). Al iniciar sesión,
  si el hash guardado usa parámetros viejos, se vuelve a calcular.
- Reglas de la contraseña (D62-B): 8 a 64 caracteres y que no esté en una lista
  de contraseñas comunes incluida en el repositorio. Se valida en
  `entities/password_policy.py`; la lista la carga un adaptador.
- **Límite de intentos (D62-F, D70):** 5 por minuto por IP en `login`,
  `password/forgot`, `verify-email/resend`, `register` (cada registro envía un
  correo y sin límite serviría para mandar correos en masa) y
  `password/change`.
- **Dónde se cuenta (D77):** en Redis cuando hay `REDIS_URL`, para que todos
  los procesos y servidores compartan el conteo.
  - `RedisRateLimiter` (`shared/adapters/redis_rate_limiter.py`) cumple el
    mismo contrato `RateLimit` que el contador en memoria: ningún controller ni
    caso de uso cambia.
  - Ventana fija de 60 s: `INCR`, `EXPIRE … NX` y `TTL` van en una sola
    transacción (`MULTI`), así una clave nunca queda sin vencimiento. Si se pasó
    el límite, `Retry-After` es el `TTL` que queda.
  - Claves `memories:ratelimit:<acción>:<ip>`, por si la instancia de Redis se
    comparte con otro proyecto.
  - Si Redis no responde (timeouts de 0,5 s, sin reintentos), se registra un
    aviso y se cuenta en memoria (`InMemoryRateLimiter`): nunca se quita el
    límite. Tras ese fallo, durante 30 s no se vuelve a probar Redis: una caída
    demora como mucho un intento cada 30 s y deja un aviso, no uno por intento.
  - Requiere Redis 7 o superior (`EXPIRE NX`); la imagen es `redis:8.2-alpine`.
  - Sin `REDIS_URL` (pruebas, API sin Docker) se usa solo el contador en memoria.
  - La IP es `request.client.host`. `X-Forwarded-For` no se lee: detrás de un
    proxy, uvicorn la toma solo de proxies de confianza (`--forwarded-allow-ips`,
    se define al desplegar). Ojo: por defecto uvicorn confía en `127.0.0.1`,
    así que con la API sin Docker un cliente local puede cambiar su IP; en
    Docker las peticiones llegan desde la red del contenedor y no aplica.
  - Redis solo guarda estos contadores: sin persistencia en disco. Las sesiones
    siguen en PostgreSQL (D56).
- **Correos (D62-C):** los casos de uso usan el puerto `EmailSender`. En desarrollo
  se envía por SMTP a **Mailpit** (en Docker Compose), que captura los correos
  y los muestra en su web; en los tests, un enviador falso. El proveedor real
  se elige al desplegar.
- **Correos después de responder (D74):** `password/forgot` y
  `verify-email/resend` usan `DeferredEmailSender`
  (`shared/adapters/deferred_email_sender.py`), que cumple el mismo puerto
  `EmailSender` pero solo guarda el correo. La dependencia de cada petición
  (`open_request_scope` en `main.py`) crea uno y programa su `flush()` con
  `BackgroundTasks` de FastAPI, que corre después de enviar la respuesta. Los
  casos de uso no cambian. Si el envío falla, se registra en el log sin el
  contenido del correo (lleva el token) y no se reintenta: la persona puede
  pedir otro. `register` sigue enviando dentro de la petición.
  - La dependencia usa `scope="function"`: la sesión de base se cierra antes de
    responder, así un SMTP lento no retiene conexiones del pool.
  - Si la petición termina en error, no se envía nada (la respuesta de error no
    lleva las tareas). Si algún endpoint asigna su propio `background` a la
    respuesta, los correos diferidos se perderían: no hacerlo.
- `users` usará la dependencia de "usuario actual" que expone `auth`; no lee
  `user_session` directamente.

## 6. Riesgos

- **Enumeración de cuentas:** login, reenvío y recuperación responden igual
  exista o no la cuenta. La única excepción es "verifica tu correo", que solo
  aparece con la contraseña correcta (D62-E). El registro sí revela que un
  correo o usuario ya existe: es inevitable para que la persona elija otro.
- **Límite de intentos con Redis caído:** se vuelve al contador en memoria, que
  cuenta por proceso; mientras dure la caída, con varios procesos el límite real
  se multiplica. Cada 30 s un intento espera hasta 0,5 s al volver a probar. Riesgo aceptado (D77): es mejor que quitar el límite o que
  rechazar todo.
- **Ventana fija:** quien reparte intentos justo antes y después del cambio de
  minuto puede hacer hasta 10 en pocos segundos. Aceptado: sigue frenando la
  fuerza bruta (el contador en memoria usa ventana deslizante).
- **Tiempo de respuesta en `password/forgot` y `verify-email/resend`:** el
  cuerpo y el código son idénticos exista o no la cuenta, pero si existe se
  enviaba el correo dentro de la petición y la respuesta tardaba más, lo que
  podía revelar qué correos tienen cuenta. Resuelto con D74: el correo sale
  después de responder. Queda una diferencia de una consulta y la firma de un
  token (milisegundos), despreciable frente al envío SMTP.
- **Correo en segundo plano que falla (D74):** la persona ya recibió la
  respuesta y no se entera; solo queda en el log. Riesgo aceptado: la respuesta
  ya es la misma exista o no la cuenta, y puede pedir otro correo.
- **Enlace de recuperación y suspensión:** un enlace pedido antes de suspender
  la cuenta todavía cambia la contraseña. Es inofensivo, porque la cuenta
  suspendida igual no puede entrar (RN-17).
- **Dos usos simultáneos del mismo enlace:** se cubren leyendo la cuenta con
  `FOR UPDATE`; el segundo ya ve la fecha nueva y se rechaza (RN-19).
- **Carrera en la rotación:** dos `refresh` simultáneos con el mismo token
  pueden revocar una sesión legítima (por ejemplo, dos pestañas). Es el costo
  aceptado de detectar reuso; el cliente debe serializar las renovaciones. En
  la base, la sesión se lee con `FOR UPDATE` para que dos rotaciones no se
  pisen.
- **Reloj:** los vencimientos se calculan en UTC en el servidor.
