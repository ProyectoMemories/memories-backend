# Memories — Backend

API de [Memories](docs/product/prd-resumen.md): una aplicacion para guardar
momentos importantes con su contexto y volver a encontrarlos con el tiempo.

FastAPI · Python 3.12 · PostgreSQL · SQLAlchemy async · Alembic · Redis ·
MinIO/S3 · Docker.

La app movil y web vive en el repositorio `memories-frontend` (Flutter).

---

## Arrancar en local

Requisitos: Docker Desktop.

```bash
cp .env.example .env          # y cambia las contrasenas
docker compose up -d --build
```

Eso levanta PostgreSQL, Redis, MinIO (con su bucket ya creado) y la API, que
aplica las migraciones al arrancar.

| Que | Donde |
|---|---|
| API | http://localhost:8000 |
| Documentacion interactiva | http://localhost:8000/docs |
| Estado del servicio | http://localhost:8000/health/ready |
| Consola de MinIO | http://localhost:9001 |
| Adminer (opcional) | `docker compose --profile tools up -d` → http://localhost:8080 |

Crear el superusuario inicial:

```bash
docker compose exec api python scripts/seed.py
```

Ver los logs de la API: `docker compose logs -f api`.
Parar todo: `docker compose down` (con `-v` borra tambien los datos).

### Sin Docker

```bash
python -m venv .venv && .venv\Scripts\activate    # PowerShell
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Necesitas PostgreSQL a mano. Con `CACHE_PROVIDER=memory` y
`STORAGE_PROVIDER=local` no hacen falta ni Redis ni MinIO.

---

## Trabajo diario

```bash
pytest                                   # pruebas
ruff check . && ruff format .            # estilo
mypy app                                 # tipos
lint-imports                             # reglas de arquitectura
alembic revision --autogenerate -m "..." # nueva migracion
alembic upgrade head                     # aplicarla
```

Las pruebas usan su propio esquema (`memories_test`) en la misma base, cache en
memoria y disco local: no tocan tus datos de desarrollo.

---

## Como esta organizado

Monolito modular con Clean Architecture. Cada modulo es una capacidad del
producto y dentro repite la misma estructura:

```
app/modules/<modulo>/
├── domain/           reglas de negocio (Python puro, sin ORM ni FastAPI)
├── application/      casos de uso, uno por archivo
├── infrastructure/   modelos (una tabla por archivo), repositorios, mappers
└── interfaces/       esquemas Pydantic, routers y cableado de dependencias
```

El mapa completo, con la razon de cada decision, esta en
[docs/arquitectura.md](docs/arquitectura.md) y en [docs/adr/](docs/adr/).
Las reglas de trabajo, en [CLAUDE.md](CLAUDE.md).

## Endpoints

| Metodo | Ruta | Que hace |
|---|---|---|
| POST | `/api/v1/auth/register` | Crear cuenta |
| POST | `/api/v1/auth/login` | Iniciar sesion |
| POST | `/api/v1/auth/refresh` | Renovar la sesion |
| POST | `/api/v1/auth/logout` | Cerrar sesion |
| GET/PATCH | `/api/v1/users/me` | Perfil propio |
| GET | `/api/v1/users` | Listar usuarios (superusuario) |
| POST | `/api/v1/photos` | Subir una fotografia |
| GET | `/api/v1/photos/{id}/raw` | Descargar la imagen por la API |
| DELETE | `/api/v1/photos/{id}` | Descartar una foto sin recuerdo |
| POST/GET | `/api/v1/memories` | Crear y listar recuerdos |
| GET | `/api/v1/memories/calendar` | Recuerdos por dia (vista calendario) |
| GET | `/api/v1/memories/revive` | Volver a descubrir recuerdos |
| GET/PATCH/DELETE | `/api/v1/memories/{id}` | Detalle, edicion y borrado |
| POST | `/api/v1/memories/{id}/photos` | Anadir fotografias |
| DELETE | `/api/v1/memories/{id}/photos/{photo_id}` | Quitar una fotografia |
