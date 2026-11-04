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

## Puesta en marcha paso a paso (Windows)

Sigue estos pasos en orden la primera vez. Al terminar tendrás la API, la base
de datos con todas sus tablas, MinIO y Mailpit corriendo en tu PC, y las pruebas
en verde. Los comandos son para **PowerShell** (por ejemplo, la terminal de
VS Code) y se ejecutan **desde la carpeta del repositorio**.

### 1. Instala las herramientas

| Herramienta | Para qué | Cómo comprobarlo |
|---|---|---|
| [Python 3.12](https://www.python.org/downloads/) | Pruebas y lint | `py -3.12 --version` |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) (con WSL 2) | API, base de datos, MinIO y Mailpit | `docker --version` y Docker Desktop abierto |
| [GitHub Desktop](https://desktop.github.com/) o Git | Bajar el código | — |

Al instalar Python, marca **"Add python.exe to PATH"**.

### 2. Baja la última versión de `main`

- **Si aún no tienes el repo:** en GitHub Desktop, File → Clone repository →
  `ProyectoMemories/memories-backend`.
- **Si ya lo tenías:** en GitHub Desktop cámbiate a la rama `main` →
  **Fetch origin** → **Pull origin**.

Si tu `main` local tiene commits que no están en GitHub (por ejemplo, un merge
hecho en tu PC), GitHub no te dejará subirlos. Déjalo igual que GitHub (borra
todo lo que tengas en `main` local y no esté en GitHub):

```powershell
git checkout main
git fetch origin
git reset --hard origin/main
```

### 3. Limpia lo que quedó del código anterior (solo si ya tenías el repo)

El código viejo se borró en `main`, pero pueden quedar restos en tu PC.

**Contenedores viejos.** Ocupan los mismos puertos y hacen fallar Docker con
"ports are not available":

```powershell
docker ps -a --filter "name=memories_"
docker rm -f memories_db memories_redis memories_minio memories_minio_init memories_api memories_adminer
```

Si alguno no existe, Docker solo lo avisa. Los contenedores nuevos se llaman
`memories-db-1`, `memories-api-1`, etc. (con guion): no los borres.

**Archivos viejos que git no borró.** Muestra los archivos que están en tu
carpeta pero no en el repositorio:

```powershell
git clean -n -d
```

Si en la lista aparecen archivos tuyos que quieras conservar, cópialos fuera
del repositorio. Después bórralos con `git clean -f -d`. No toca `.env`,
`.venv` ni las cachés (están en `.gitignore`).

### 4. Crea el entorno de Python e instala las dependencias

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Si `Activate.ps1` da error de permisos, ejecuta una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y vuelve a intentarlo.
Sabes que el entorno está activo porque la terminal empieza con `(.venv)`.

### 5. Crea tu `.env`

```powershell
Copy-Item .env.example .env -Force
```

Funciona tal cual en local. Si cambias `POSTGRES_PASSWORD`, cámbiala también
dentro de `DATABASE_URL` y `TEST_DATABASE_URL`. El `.env` nunca se sube a
GitHub.

`SECRET_KEY` firma los tokens de sesión y de los correos. El valor de ejemplo
sirve en tu PC; si quieres una propia:
`python -c "import secrets; print(secrets.token_urlsafe(48))"`.

### 6. Levanta Docker

Con Docker Desktop abierto:

```powershell
docker compose up -d --build
docker compose ps -a
```

La primera vez tarda unos minutos porque descarga las imágenes. Debes ver
`api`, `db`, `minio` y `mailpit` en **healthy**, y `minio-init` en
**Exited (0)** (creó el bucket de fotos y terminó). Si algo falla, revisa
[Si falla con "ports are not available"](#si-falla-con-ports-are-not-available).

### 7. Crea las tablas de la base de datos

```powershell
docker compose exec api alembic upgrade head
docker compose exec api alembic current
docker compose exec db psql -U memories -d memories -c "\dt"
```

Debes ver `0001 (head)` y **17 tablas** (las 16 del modelo más
`alembic_version`).

### 8. Corre el lint y las pruebas

```powershell
ruff check .
ruff format --check .
pytest
```

Debes ver `All checks passed!`, los archivos ya formateados y todas las
pruebas en verde, **ninguna `skipped`**. Si salen `skipped`, la base no está
levantada o falta `TEST_DATABASE_URL` en tu `.env`.

### 9. Comprueba en el navegador

| Qué | Dónde | Qué debes ver |
|---|---|---|
| API | http://localhost:8001/health | `{"status":"ok"}` |
| Documentación de la API | http://localhost:8001/docs | La documentación interactiva |
| MinIO | http://localhost:9011 | Entra con `MINIO_ROOT_USER` y `MINIO_ROOT_PASSWORD` del `.env`; debe estar el bucket `memories-photos` |
| Mailpit | http://localhost:8025 | La bandeja de correos que envía la API |

Listo: estás al día. Para probar el registro, sigue
[Probar la API desde /docs](#probar-la-api-desde-docs). Para apagar todo,
`docker compose down` (conserva los datos).

## Probar la API desde /docs

Con Docker levantado y las tablas creadas (pasos 6 y 7), abre
http://localhost:8001/docs. En cada endpoint: **Try it out** → edita el
cuerpo → **Execute**.

**Registrarse** (`POST /api/v1/auth/register`):

```json
{
  "username": "ana.rios",
  "email": "ana@correo.com",
  "password": "caballo bateria grapa",
  "first_name": "Ana",
  "paternal_surname": "Ríos",
  "maternal_surname": null,
  "birth_date": "2000-05-17",
  "accepts_privacy_policy": true
}
```

Debe responder **201** con la cuenta en `"status": "unverified"`.

**Ver el correo en Mailpit:** abre http://localhost:8025. Llega
"Confirma tu correo en Memories" para `ana@correo.com`. El enlace apunta a la
app web (`http://localhost:3000/verify-email?token=...`), que todavía no
existe: no lo abras, **copia lo que va después de `token=`**.

**Verificar el correo** (`POST /api/v1/auth/verify-email`): pega el token en
`{"token": "..."}`. Debe responder **204** y, en DBeaver, la cuenta queda en
`active` con `email_verified_at` lleno. Repetirlo vuelve a dar 204 y no cambia
nada.

**Reenviar el enlace** (`POST /api/v1/auth/verify-email/resend`) con
`{"email": "ana@correo.com"}`: responde **202** siempre, exista o no la
cuenta. Solo llega un correo nuevo si la cuenta sigue sin verificar. La sexta
vez en un minuto responde **429**.

Los errores llegan como `{"code": "...", "message": "..."}`; por ejemplo,
`username_taken`, `underage` o `password_too_common`.

## Ver las tablas con DBeaver

Con Docker levantado (`db` en **healthy**):

1. En DBeaver: **Database → New Database Connection** → **PostgreSQL** →
   Next.
2. Llena la conexión con los valores del `.env`:

   | Campo | Valor |
   |---|---|
   | Host | `localhost` |
   | Port | `5433` (no 5432) |
   | Database | `memories` |
   | Username | `memories` |
   | Password | `cambiame` |

   Son los valores por defecto de `.env.example`, solo para tu PC. Si cambiaste
   `POSTGRES_PASSWORD` en tu `.env`, usa esa.
3. **Test Connection.** La primera vez DBeaver pide descargar el driver de
   PostgreSQL: acepta con **Download**. Cuando diga "Connected", pulsa
   **Finish**.
4. Las tablas están en `memories` → Databases → `memories` → Schemas →
   **public** → **Tables**: las 16 del modelo más `alembic_version`. Para ver
   el diagrama con las relaciones: clic derecho en `public` → **View Diagram**.

- **No crees ni cambies tablas desde DBeaver.** Todo cambio de esquema va en
  una migración de Alembic; si no, tu base deja de coincidir con la de los
  demás. Mirar datos y hacer consultas, sin problema.
- La base `memories_test` la crean y la borran las pruebas: no trabajes en ella.
- "Connection refused": Docker no está levantado o el puerto no es 5433.
  "password authentication failed": la contraseña no coincide con tu `.env`.

## Cada vez que bajes cambios de `main`

Después de un **Pull origin** en `main`:

1. Si el PR cambió `.env.example`, vuelve a copiarlo:
   `Copy-Item .env.example .env -Force` (y repite tus contraseñas si las
   cambiaste).
2. Con `(.venv)` activo: `pip install -r requirements-dev.txt`
3. `docker compose up -d --build`
4. `docker compose exec api alembic upgrade head`
5. `pytest`

Si alguno falla, lo más probable es que te saltaste el paso 1.

**Si el PR cambió la migración `0001`** (lo dice su descripción): hasta el
primer despliegue el esquema se corrige en la misma `0001` (D64), así que tu
base local tiene que recrearse. En lugar del paso 4:

```powershell
docker compose exec api alembic downgrade base
docker compose exec api alembic upgrade head
```

Esto borra las tablas y los datos de prueba de tu base local y la vuelve a
crear con el esquema nuevo.

Nunca hagas merge ni commits en `main` desde tu PC: `main` solo se actualiza
con Pull. Para trabajar, crea tu rama (ver [Cómo contribuir](#cómo-contribuir)).

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
