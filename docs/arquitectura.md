# Arquitectura del backend

Mapa para responder "donde vive esto" sin recorrer el repositorio. El producto
esta en [docs/product/prd-resumen.md](product/prd-resumen.md); el porque de cada
decision, en [docs/adr/](adr/).

---

## 1. Capas

```
interfaces  →  infrastructure  →  application  →  domain
   HTTP           Postgres,          casos de       reglas de
   Pydantic       S3, Redis          uso            negocio
```

La flecha es la direccion permitida de los imports. Hacia el otro lado, nunca.
Lo verifica `lint-imports` en CI ([ADR 0001](adr/0001-clean-architecture-en-modulos.md)).

| Capa | Puede importar | Jamas importa |
|---|---|---|
| `domain` | `app.shared` | FastAPI, SQLAlchemy, Pydantic, Redis, boto3, `app.core`, `app.config` |
| `application` | `domain`, puertos de `app.core` | FastAPI, SQLAlchemy, Redis, boto3 |
| `infrastructure` | `domain`, `application`, `app.core`, `app.config` | otras `infrastructure` ajenas |
| `interfaces` | todas las de su modulo | la `infrastructure` de otro modulo |

## 2. Estructura

```
app/
├── main.py                 crea la app, monta routers, /health, cierra /docs fuera de local
├── api.py                  monta los routers de /api/v1  ← anadir un modulo = una linea
├── config/
│   ├── settings.py         pydantic-settings; los secretos no tienen valor por defecto
│   └── database.py         motor async y sesion por peticion (commit al final)
├── core/                   infraestructura transversal, sin negocio
│   ├── security/
│   │   ├── hashing/        RNF-08: port, bcrypt, argon2, service, factory
│   │   ├── tokens/         emision y validacion de JWT
│   │   └── dependencies.py get_current_user, require_superuser
│   ├── storage/            RNF-09: port, s3 (MinIO y AWS), local, factory
│   ├── cache/              port, redis, memoria, factory
│   ├── middleware/         request-id y traduccion de errores a HTTP
│   ├── rate_limit.py       limite por IP y minuto
│   └── logging.py          structlog (consola en dev, JSON en produccion)
├── shared/                 nucleo compartido, puro
│   ├── errors.py           errores base (sin HTTP)
│   ├── roles.py            UserRole
│   ├── pagination.py       PageRequest / Page
│   └── db/                 Base, mixins y registry de modelos
└── modules/
    ├── users/              perfil y cuentas
    ├── auth/               sesiones (sin domain propio: no tiene reglas propias)
    └── memories/           recuerdos, fotografias, calendario y revivir
```

## 3. Modulos

| Modulo | Tiene `domain/` | Que contiene |
|---|---|---|
| `users` | si | `User`, `Email`, `RawPassword`, puerto `UserRepository` |
| `auth` | **no** | Orquesta usuarios + JWT + hashing. Puerto propio: `RefreshTokenStore` |
| `memories` | si | `Memory`, `Photo`, `revive_selector`, puertos de recuerdos y fotografias |

`memories` publica dos routers: `/memories` y `/photos`. Las fotografias cuelgan
de su propia ruta porque se suben **antes** de que el recuerdo exista, pero
pertenecen a este modulo: una fotografia sin recuerdo no tiene sentido de
negocio.

## 4. Base de datos

- Las tablas viven en el esquema predeterminado de la base. `DB_SCHEMA` permite
  moverlas a uno propio y es lo que usan los tests (`memories_test`) para
  aislarse sin necesidad de otra base de datos. En desarrollo y produccion se
  deja vacio: con un esquema propio, `--autogenerate` propone borrar y recrear
  las claves foraneas en cada ejecucion (limitacion conocida de Alembic), y eso
  acaba en migraciones sucias.
- Tres tablas, **una por archivo** ([ADR 0002](adr/0002-un-archivo-por-tabla-y-por-caso-de-uso.md)):
  `users`, `memories`, `photos`.
- `photos.memory_id` es nulo mientras la foto esta subida y sin recuerdo.
  `ON DELETE CASCADE`: borrar un recuerdo borra sus fotografias.
- Identificadores UUID generados en la aplicacion (la entidad existe antes de
  tocar la base).
- **Todo cambio de esquema es una migracion de Alembic.** Aqui si sirve
  `--autogenerate`, porque el esquema nace de los modelos. `alembic check` en CI
  detecta si alguien cambio un modelo y olvido la migracion.
- Un modelo nuevo se anade a `app/shared/db/registry.py` o Alembic no lo vera.

## 5. Unidad de trabajo

Una sesion por peticion (`config/database.py`): si el endpoint termina bien, se
hace commit; si lanza, rollback. **Los casos de uso no hacen commit**: hacen
`flush` a traves de los repositorios. Asi una peticion que toca dos agregados es
atomica sin que nadie lo coordine a mano.

## 6. Errores

El dominio lanza errores de negocio que no saben nada de HTTP
(`app/shared/errors.py`). `core/middleware/error_handlers.py` los traduce:

| Error | HTTP |
|---|---|
| `ValidationError` | 422 |
| `NotFoundError` | 404 |
| `ConflictError` | 409 |
| `AuthenticationError` | 401 |
| `PermissionDeniedError` | 403 |
| `RateLimitExceededError` | 429 |
| `StorageError` | 502 |
| cualquier otro | 500 (el detalle va al log, nunca al cliente) |

Respuesta:
`{"error": {"code": "...", "message": "...", "details": {}, "request_id": "..."}}`

## 7. Privacidad

Es una regla de arquitectura, no una precaucion:

- **Toda** operacion del repositorio de recuerdos recibe `owner_id`. Esta en la
  firma del puerto, asi que no se puede "olvidar" el filtro.
- Pedir algo ajeno responde **404, no 403**: un 403 confirmaria que existe.
- `tests/integration/test_privacy.py` intenta leer, editar y borrar datos de otra
  cuenta y exige que falle.

## 8. Lo que no esta hecho

- **Albums compartidos**: sin implementar a proposito. Ver
  [ADR 0008](adr/0008-supuestos-sobre-pendientes-del-prd.md) y `specs/albums/`.
- **Limpieza de fotografias huerfanas**: una foto subida y nunca asociada se
  queda ahi. Hara falta una tarea periodica; no hay planificador todavia.
- **Refresco de tokens tras vaciar Redis**: obliga a iniciar sesion otra vez.
