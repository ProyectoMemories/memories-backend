# Spec: cuentas y sesiones — Tareas

- [x] Entidad `User` con `Email` y `RawPassword` como objetos de valor
      · test: `tests/unit/test_password_hashing.py`
- [x] Puerto `UserRepository` y su implementacion SQLAlchemy
- [x] Tabla `users` y migracion `0001`
- [x] `PasswordHashingService` con bcrypt y Argon2 e intercambio por variable
      · test: `tests/unit/test_password_hashing.py`
- [x] `JWTService` (acceso y refresco)
- [x] Puerto `RefreshTokenStore` y su implementacion sobre `CachePort`
- [x] Caso de uso `RegisterUser`
      · test: `tests/integration/test_auth_api.py`
- [x] Caso de uso `AuthenticateUser` con re-hasheo transparente
      · test: `tests/integration/test_auth_api.py`
- [x] Caso de uso `RefreshSession` con rotacion
      · test: `test_renovar_la_sesion_invalida_el_refresh_token_usado`
- [x] Caso de uso `LogoutUser` idempotente
      · test: `test_cerrar_sesion_invalida_el_refresh_token`
- [x] Dependencias `get_current_user` y `require_superuser`
      · test: `test_listar_usuarios_es_solo_para_el_superusuario`
- [x] Rate limiting en `/auth`
- [x] Endpoints de perfil (`/users/me`) y listado para superusuario
- [x] Script `scripts/seed.py` para crear el superusuario inicial

## Siguientes (fuera del MVP)

- [ ] Recuperacion de contrasena por correo
- [ ] Verificacion del correo al registrarse
- [ ] Mitigar la diferencia de tiempos en el login (hash ficticio)
