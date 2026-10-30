# Spec: auth — Diseño

Estado: **borrador para revisión del equipo**. Los puntos marcados
[PROPUESTA] no están decididos en Drive.

## 1. Tablas (memories-physical-v1.4.sql)

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

### Cómo viaja el token de renovación (D56)

- **Android:** en el cuerpo de la respuesta de `login` y `refresh`; el cliente
  lo guarda en el almacenamiento seguro y lo manda en el cuerpo de `refresh` y
  `logout`.
- **Web:** en una cookie `HttpOnly`, `Secure`, `SameSite` con `Path` limitado a
  `/api/v1/auth`. No aparece en el cuerpo de la respuesta.
- La plataforma la declara el cliente al iniciar sesión (`platform`, más un
  `device_name` opcional) y queda guardada en la sesión.

### Protección CSRF en web

- `refresh` y `logout` en web revisan la cabecera `Origin` y la comparan con el
  dominio de la app web (variable de entorno). Si no coincide, se rechaza.
- CORS solo permite ese dominio, con credenciales. Nunca `*`.
- [PROPUESTA] `SameSite=Strict` si la API y la app web comparten el mismo sitio
  registrable; `Lax` si no. Se decide al definir los dominios de despliegue.

## 3. Reglas de sesión (D56, RN-67)

- **Token de acceso:** JWT de 15 minutos con `sub` (id de usuario) y `sid`
  (id de sesión). No se guarda.
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
| Recuperación | id de usuario, propósito `reset_password`, `password_changed_at` | P-A | al vencer o cuando cambia `password_changed_at` (RN-19) |

Cada token lleva su propósito, para que uno de verificación no sirva para
recuperar la contraseña.

## 5. Capas

```
app/modules/auth/
├── router.py        endpoints, cookies, lectura de Origin
├── service.py       registro, verificación, login, rotación, logout, contraseñas
├── repository.py    app_user, privacy_consent, user_session
├── models.py        modelos SQLAlchemy de esas tres tablas
└── schemas.py       entrada y salida
```

- La edad mínima (RN-08) se valida en el servicio, no en la base (el `.sql` lo
  deja fuera a propósito: la edad cambia con el tiempo).
- El formato del nombre de usuario se valida en el schema **y** lo impone la
  base (`ck_app_user_username_format`).
- El hash de contraseñas se usa detrás de una interfaz pequeña para poder
  cambiar el algoritmo (RNF-08, P-D).
- `users` usará la dependencia de "usuario actual" que expone `auth`; no lee
  `user_session` directamente.

## 6. Riesgos

- **Enumeración de cuentas:** registro, login, reenvío y recuperación no deben
  revelar si un correo existe más de lo necesario (ver P-E).
- **Carrera en la rotación:** dos `refresh` simultáneos con el mismo token
  pueden revocar una sesión legítima (por ejemplo, dos pestañas). Es el costo
  aceptado de detectar reuso; el cliente debe serializar las renovaciones.
- **Reloj:** los vencimientos se calculan en UTC en el servidor.
- **Correos:** sin proveedor decidido (P-C), los tests usan un enviador falso.
