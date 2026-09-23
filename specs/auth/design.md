# Spec: cuentas y sesiones — Diseno

## Contratos de la API

| Metodo | Ruta | Cuerpo | Respuesta |
|---|---|---|---|
| POST | `/api/v1/auth/register` | `{email, display_name, password}` | 201 `UserResponse` |
| POST | `/api/v1/auth/login` | `{email, password}` | 200 `SessionResponse` |
| POST | `/api/v1/auth/refresh` | `{refresh_token}` | 200 `SessionResponse` |
| POST | `/api/v1/auth/logout` | `{refresh_token?, all_devices?}` | 200 `{message}` |
| GET | `/api/v1/users/me` | — | 200 `UserResponse` |
| PATCH | `/api/v1/users/me` | `{display_name}` | 200 `UserResponse` |
| GET | `/api/v1/users` | — | 200 lista paginada (solo superusuario) |

`SessionResponse`: `{access_token, refresh_token, token_type, expires_in, user}`.

Todos los endpoints de `/auth` llevan rate limiting por IP
(`RATE_LIMIT_AUTH_PER_MINUTE`, 10 por defecto).

## Modelo de datos

Tabla `users`: `id` (UUID), `email` (unico), `display_name`, `password_hash`,
`role` (enum `user_role`: `user` | `superuser`), `is_active`, `created_at`,
`updated_at`.

Los tokens de refresco **no** van a la base: viven en Redis bajo
`auth:refresh:{user_id}` como `{jti: vencimiento}`. Cerrar todas las sesiones es
borrar una clave.

## Reparto por capas

| Capa | Que vive aqui |
|---|---|
| `users/domain` | `User`, `Email`, `RawPassword`, `UserRepository` (puerto), errores |
| `users/application` | `GetUserProfile`, `UpdateUserProfile`, `ListUsers` |
| `users/infrastructure` | `user_model.py`, mapper, repositorio SQLAlchemy |
| `auth/application` | `RegisterUser`, `AuthenticateUser`, `RefreshSession`, `LogoutUser`, puerto `RefreshTokenStore` |
| `auth/infrastructure` | `CacheRefreshTokenStore` (sobre `CachePort`) |
| `core/security` | `JWTService`, `PasswordHashingService`, `get_current_user` |

`auth` no tiene `domain/`: no tiene reglas propias, orquesta las de `users` con
los servicios de seguridad ([ADR 0001](../../docs/adr/0001-clean-architecture-en-modulos.md)).

## Decisiones

- JWT HS256, acceso de 30 minutos, refresco de 30 dias con rotacion:
  [ADR 0003](../../docs/adr/0003-autenticacion-jwt-hs256.md).
- Hashing intercambiable con re-hasheo transparente al iniciar sesion:
  [ADR 0004](../../docs/adr/0004-hashing-de-contrasenas-intercambiable.md).
- Redis como almacen de tokens de refresco:
  [ADR 0006](../../docs/adr/0006-para-que-usamos-redis.md).

## Riesgos

| Riesgo | Mitigacion |
|---|---|
| Robo del token de acceso (sin cookie HttpOnly en web) | Token corto y rotacion del de refresco |
| Redis vacio o caido | Todo el mundo vuelve a iniciar sesion; el rate limiting deja pasar en vez de bloquear el servicio |
| Desactivar a alguien no es inmediato | Hasta 30 minutos de margen; documentado en `core/security/dependencies.py` |
