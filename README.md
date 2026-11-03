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

El CI de GitHub Actions corre lo mismo en cada Pull Request.

## Entorno local (Docker)

Levanta PostgreSQL 18, MinIO (con el bucket de fotos ya creado) y Mailpit.

```powershell
copy .env.example .env      # la primera vez; luego cambia las contraseñas
docker compose up -d
docker compose ps           # db, minio y mailpit deben decir "healthy"
```

| Servicio | Dónde |
|---|---|
| PostgreSQL | `localhost:5433` (usuario, clave y base del `.env`) |
| Consola de MinIO | http://localhost:9011 |
| API S3 de MinIO | http://localhost:9010 |
| Mailpit (correos) | http://localhost:8025 · SMTP en `localhost:1025` |

- Ver los logs: `docker compose logs -f`
- Apagar: `docker compose down` (los datos se conservan)
- Borrar también los datos: `docker compose down -v` (¡no se puede deshacer!)

Si un puerto ya está ocupado en tu PC, cámbialo en tu `.env`.

## Cómo levantar la API

Se completa con `feat/app-skeleton` y `feat/db-initial-migration`.

## Cómo contribuir

1. Crea tu rama desde `main`: `feat/…`, `fix/…`, `chore/…` o `docs/…`.
2. Si es una funcionalidad nueva, primero el spec en `specs/<feature>/`.
3. Abre un Pull Request hacia `main` y completa la plantilla.
4. Revisa tu propio diff y, cuando el CI pase, fusiona tu PR.

`main` está protegido: no acepta push directo, force push ni borrado.
