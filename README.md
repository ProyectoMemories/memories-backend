# Memories — Backend

API de Memories: FastAPI + Python 3.12, PostgreSQL 18 y almacenamiento
compatible con S3 (MinIO en local).

Producto, decisiones, reglas de negocio, requisitos y arquitectura viven en
Google Drive, carpeta "Proyecto Recuerdos". Aquí solo va lo necesario para
levantar y probar el proyecto. Las reglas para trabajar con Claude Code están en
[CLAUDE.md](CLAUDE.md) y los specs en [specs/](specs/).

El código anterior, escrito con el PRD v3.0, se conserva en el tag
`legacy-prd-v3.0`.

## Requisitos

- Python 3.12
- Docker Desktop (en Windows, con el backend WSL 2)

## Calidad: lint y pruebas

Windows (PowerShell), desde la carpeta del repositorio:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
ruff check .
ruff format --check .
pytest
```

macOS o Linux: igual, pero `python3.12 -m venv .venv` y
`source .venv/bin/activate`.

Las pruebas de la base (`tests/db/`) necesitan PostgreSQL: levántalo con
`docker compose up -d db` y deja `TEST_DATABASE_URL` en tu `.env` (viene en
`.env.example`). Usan una base aparte, `memories_test`, que se borra y se crea en
cada corrida: nunca tocan tus datos. Si la base no está levantada, esas pruebas
se saltan con un aviso (en el CI, en cambio, fallan).

El CI de GitHub Actions corre lo mismo en cada Pull Request, contra
PostgreSQL 18.

## Entorno local (Docker)

Levanta la API, PostgreSQL 18, MinIO (con el bucket de fotos ya creado) y
Mailpit.

```powershell
copy .env.example .env      # la primera vez; luego cambia las contraseñas
docker compose up -d --build
docker compose ps           # api, db, minio y mailpit deben decir "healthy"
```

| Servicio | Dónde |
|---|---|
| API | http://localhost:8001/health · documentación en http://localhost:8001/docs |
| PostgreSQL | `localhost:5433` (usuario, clave y base del `.env`) |
| Consola de MinIO | http://localhost:9011 |
| API S3 de MinIO | http://localhost:9010 |
| Mailpit (correos) | http://localhost:8025 · SMTP en `localhost:1025` |

- Ver los logs: `docker compose logs -f`
- Apagar: `docker compose down` (los datos se conservan)
- Borrar también los datos: `docker compose down -v` (¡no se puede deshacer!)

### Migraciones de la base

La primera vez, y cada vez que entre una migración nueva:

```powershell
docker compose exec api alembic upgrade head
docker compose exec api alembic current     # debe decir "(head)"
```

Para deshacer la última migración: `docker compose exec api alembic downgrade -1`
(borra tablas y sus datos; úsalo solo en tu entorno local).

La API se recarga sola cuando guardas un archivo de `app/`. Si cambias
`requirements.txt` o el `Dockerfile`, vuelve a ejecutar
`docker compose up -d --build`.

### Si falla con "ports are not available"

Otro programa ya usa ese puerto en tu PC. Revisa, en este orden:

1. **Contenedores viejos** (por ejemplo, del código anterior):
   `docker ps -a`. Si ves alguno que no es de este proyecto usando los mismos
   puertos, detenlo y bórralo desde Docker Desktop o con
   `docker rm -f <nombre>`.
2. **Otro PostgreSQL instalado en Windows** en el puerto 5433:
   `netstat -ano | findstr :5433`. Detén ese servicio o cambia
   `POSTGRES_HOST_PORT` en tu `.env`.
3. Lo mismo vale para los demás puertos del `.env` (8001, 9010, 9011, 1025,
   8025).

## API sin Docker (opcional)

Con el entorno virtual activado y la base levantada por Docker:

```powershell
pip install -r requirements-dev.txt
uvicorn app.main:create_app --factory --reload
```

Lee la configuración de tu `.env` y queda en http://localhost:8000.

## Cómo contribuir

1. Crea tu rama desde `main`: `feat/…`, `fix/…`, `chore/…` o `docs/…`.
2. Si es una funcionalidad nueva, primero el spec en `specs/<feature>/`.
3. Abre un Pull Request hacia `main` y completa la plantilla.
4. Revisa tu propio diff y, cuando el CI pase, fusiona tu PR.

`main` está protegido: no acepta push directo, force push ni borrado.
