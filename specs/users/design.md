# Spec: users — Diseño

Fase: Arquitectura e Implementación. Clean Architecture por módulo (D69) y las
reglas de CLAUDE.md §7.

## 1. Decisiones que este diseño necesita (por registrar en el 01)

| # | Decisión | Por qué |
|---|---|---|
| D81 | El módulo `users` es dueño de los datos del perfil en `app_user` (nombres y fecha de nacimiento; luego, editarlos). `auth` sigue siendo dueño de las credenciales, el estado de la cuenta y las sesiones. Cada módulo lee la tabla con su propio gateway y nunca importa las entidades, gateways ni modelos ORM del otro (CLAUDE.md §7). | Frontera clara para editar el perfil (con la fecha fija) sin que `auth` crezca con cosas de perfil. Aprobado por Victor el 2026-11-27 (opción A). |
| D82 | `GET /users/me` y el nombre en la app se hacen antes de F7 del frontend de auth. Excepción a D78, que ponía `users` después de F7. | Con varias cuentas de prueba no se sabe con cuál se entró; es corto y se ve en cada pantalla. Aprobado por Victor el 2026-11-27. |

Regla para el 05 (**[PROPUESTA]**, aprobada por Victor): "Después del registro,
la fecha de nacimiento no se puede cambiar desde la app."

## 2. Contrato de la API

`GET /api/v1/users/me` · seguridad `HTTPBearer` (token de acceso)

| Respuesta | Cuándo | Cuerpo |
|---|---|---|
| 200 | Sesión válida | `ProfileResponse` |
| 401 | Sin token, token vencido, inválido o de una sesión cerrada | `{code, message}`: `not_authenticated` o `access_token_expired` |

```json
{
  "id": "0192f0c4-…",
  "username": "victor.vergara",
  "email": "victor@ejemplo.pe",
  "first_name": "Victor",
  "paternal_surname": "Vergara",
  "maternal_surname": null
}
```

- Solo lee el perfil de quien hace la petición: el id sale del token
  (`CurrentUser` de `auth`), nunca de la URL ni del cuerpo. Así no hay forma de
  pedir el de otra cuenta (RNF-02).
- No devuelve `birth_date`, `password_hash`, `status` ni `is_superuser`.
- Si la cuenta desapareció entre la autenticación y la lectura (carrera con una
  eliminación), responde 401 `not_authenticated`, como si la sesión ya no
  valiera.

## 3. Capas (estructura de CLAUDE.md §5)

```
app/modules/users/
├── entities/profile.py            Profile: datos que muestra el perfil (Python puro)
├── use_cases/
│   ├── ports.py                   ProfileGateway (Protocol): get(user_id) -> Profile | None
│   └── get_my_profile.py          GetMyProfile.execute(user_id) -> Profile
├── adapters/
│   ├── controllers/
│   │   ├── dependencies.py        UsersUseCases (Protocol) y UseCases, como en auth
│   │   └── router.py              GET /api/v1/users/me con CurrentUser de auth
│   ├── presenters/
│   │   ├── responses.py           ProfileResponse (Pydantic)
│   │   └── profile_presenter.py   Profile → ProfileResponse
│   └── gateways/
│       ├── orm_models.py          ProfileRecord: solo las columnas del perfil
│       └── profile_gateway.py     SqlProfileGateway
└── frameworks/composition.py      UsersModule.use_cases(session)
```

- **Cómo lee `app_user` sin tocar `auth`:** `ProfileRecord` mapea solo `id`,
  `username`, `email`, `first_name`, `paternal_surname` y `maternal_surname`,
  en su propio `DeclarativeBase` (otra `MetaData`). Si usara el `Base` de
  `shared`, SQLAlchemy se quejaría de dos clases para la misma tabla. Las
  migraciones no cambian: se escriben a mano (CLAUDE.md §8) y la tabla ya
  existe.
- **Entre módulos:** `users` solo importa de `auth` la dependencia
  `CurrentUser` (`auth.adapters.controllers.dependencies`), como permite
  CLAUDE.md §7. `CurrentUser` ya comprueba la firma, el vencimiento, la sesión
  y que la cuenta siga activa.
- **Composición:** `main.open_request_scope` deja `request.state.users =
  users_module.use_cases(session)`, con la misma sesión de base de la
  petición; `create_app` monta el router de `users`.
- **import-linter** (`pyproject.toml`): contratos nuevos para `users`, iguales
  a los de `auth` (capas, entidades puras, casos de uso sin HTTP ni SQL,
  adaptadores sin `frameworks/`), más uno que prohíbe a `users` importar
  `auth.entities`, `auth.use_cases` salvo `authenticate`, `auth.adapters.gateways`
  y `auth.frameworks`.

## 4. Pruebas (con `backend-design:testing-with-discernment`)

- Interactor con un doble del gateway: devuelve el perfil; si no existe,
  `ProfileNotFoundError` (de `users/use_cases/errors.py`, código
  `not_authenticated`). No se reutiliza el error de `auth` porque las reglas
  de `users` no importan `auth` (contrato "Las reglas de users no conocen auth").
- Gateway contra PostgreSQL real (`tests/db/`): lee las columnas del perfil y
  `maternal_surname` vacío como `None`.
- API (`TestClient`):
  - sin token → 401 `not_authenticated`;
  - token de una sesión cerrada → 401;
  - con sesión → 200 con los datos propios y sin `birth_date` ni `status`;
  - **dos cuentas: cada una recibe solo lo suyo** (RNF-02, obligatoria).
- `lint-imports` en verde con los contratos nuevos (prueba de que la frontera
  se respeta).

## 5. Riesgos

- **Dos mapeos de `app_user`** (`auth` y `users`): si cambia una columna del
  perfil, hay que tocar los dos. Es el costo de la frontera; las columnas del
  perfil cambian poco y la `0001` es la fuente de verdad.
- **Un módulo nuevo sin contratos de import-linter** permitiría saltarse la
  frontera sin que el CI avise: los contratos van en la primera tarea.
- **Guía del backend en Drive:** se actualiza en el mismo PR (endpoint nuevo y
  cómo probarlo).
