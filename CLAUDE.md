# CLAUDE.md — Memories Backend

## Rol

Actuas como desarrollador del equipo de Memories (Joey Flores, Victor Avalos,
Victor Vergara). Sigues **Spec-Driven Development**: primero el spec, despues el
codigo. Trabajas por tareas pequenas y respetas la estructura de este documento.

Este repositorio es **solo el backend**. La aplicacion Flutter vive en
`memories-frontend`, con su propio CLAUDE.md.

---

## 1. Que es Memories

Un espacio privado para guardar momentos importantes con su contexto y volver a
ellos con el tiempo. La galeria del telefono guarda fotografias; Memories guarda
**el significado** que alguien decide asociarles.

La experiencia central: elegir fotos del telefono → anadir el contexto →
guardarlo como recuerdo → volver a descubrirlo mas adelante.

Resumen completo en [docs/product/prd-resumen.md](docs/product/prd-resumen.md).
Fase 1 = MVP, proyecto de portafolio; los usuarios son los propios integrantes.

**Cinco principios que mandan sobre cualquier idea tecnica:**

1. **El usuario decide.** Memories no genera recuerdos por su cuenta.
2. **La IA no es una dependencia.** El flujo principal funciona sin IA. No se
   anade ninguna llamada a modelos.
3. **No es una galeria.** Las fotos son el soporte; el producto es el contexto.
4. **Privacidad por defecto.** Nada es publico. Compartir es siempre una decision
   explicita del dueno.
5. **Terminar antes que ampliar.** Una idea nueva se registra como "fuera del
   MVP" y solo entra si los tres lo deciden.

**Fuera del alcance (no lo construyas aunque parezca facil):** IA de cualquier
tipo, integraciones con Google Photos o iCloud, video y audio, funciones sociales
(amigos, likes, comentarios, perfiles publicos) y todo lo comercial.

**El album compartido no esta implementado a proposito.** El PRD deja abierto que
es un album (pendiente P17). Antes de tocarlo, lee `specs/albums/requirements.md`
y espera la decision del equipo.

---

## 2. Stack

Python 3.12 · FastAPI · SQLAlchemy 2 async (asyncpg) · Alembic · Pydantic v2 ·
PostgreSQL 16 · Redis · MinIO/S3 · structlog · pytest · Docker Compose ·
GitHub Actions.

## 3. Comandos

```bash
docker compose up -d --build              # todo el entorno local
docker compose logs -f api                # ver la API
docker compose exec api python scripts/seed.py   # crear el superusuario
docker compose down                       # parar (con -v borra los datos)

pytest                                    # pruebas (no necesitan Redis ni MinIO)
ruff check . && ruff format .             # estilo
mypy app                                  # tipos
lint-imports                              # reglas de arquitectura
alembic revision --autogenerate -m "..."  # nueva migracion
alembic upgrade head                      # aplicarla
```

## 4. Estructura (respetala)

```
CLAUDE.md / CLAUDE.local.md    memoria del proyecto / personal (local, en .gitignore)
.github/workflows/             CI
docker-compose.yml             db + redis + minio + api
.env.example                   plantilla de variables (el .env NUNCA se sube)
docs/                          producto y arquitectura
docs/adr/                      decisiones de arquitectura
specs/<feature>/               requirements.md, design.md, tasks.md
alembic/versions/              migraciones
tests/                         espejo de app/ (unit/ e integration/)
app/
├── main.py · api.py           app FastAPI y montaje de routers
├── config/                    settings.py, database.py
├── core/                      security/ (hashing, tokens), storage/, cache/,
│                              middleware/, rate_limit.py, logging.py
├── shared/                    errors, roles, pagination, db/ (Base, mixins, registry)
└── modules/<modulo>/
    ├── domain/                entidades, objetos de valor, errores, PUERTOS
    ├── application/           casos de uso (uno por archivo)
    ├── infrastructure/        models/ (una tabla por archivo), repositories/, mappers/
    └── interfaces/http/       schemas/, router.py, dependencies.py
```

- No crees carpetas ni archivos de primer nivel sin preguntar.
- Nunca subas `.env`, `CLAUDE.local.md` ni `settings.local.json`.
- **Nombres de archivos, carpetas, clases y variables en ingles y sin tildes.**
  Comentarios, documentacion, commits y mensajes para la persona, en espanol.

---

## 5. Flujo obligatorio: Spec-Driven Development

1. **Sin spec no hay codigo.** Antes de implementar, comprueba que existe
   `specs/<feature>/`. Si no existe, creala y **detente** para que la revisemos.
2. **requirements.md**: historias de usuario y criterios de aceptacion
   verificables (Dado / Cuando / Entonces). Enlaza la capacidad del PRD (CP-0x).
3. **design.md**: contratos de la API, modelo de datos, capas que se tocan,
   riesgos. Si hay una decision de arquitectura, escribe un ADR en
   `docs/adr/NNNN-titulo.md`.
4. **tasks.md**: tareas pequenas, ordenadas por dependencia, cada una con su
   test. Se marcan `[x]` al terminar.
5. Implementa **una tarea a la vez**. Antes de cerrarla: `pytest`, `ruff`, `mypy`
   y `lint-imports`.
6. Si la implementacion se desvia del spec, **actualiza el spec primero** y
   avisa.

---

## 6. Reglas de arquitectura

La direccion de los imports es `interfaces → infrastructure → application →
domain`, y no al reves. Tres reglas que **verifica el CI** con `lint-imports`:

1. El dominio no importa FastAPI, SQLAlchemy, Pydantic, Redis, boto3, `app.core`
   ni `app.config`. Python puro.
2. La aplicacion no importa el framework web ni el ORM. Recibe **puertos**
   (Protocol), nunca clases concretas.
3. **Un modulo no toca la infraestructura de otro.** Si necesita algo de otro
   modulo, usa su dominio (puertos, entidades) o su `dependencies.py`.

Ademas:

- **Si un modulo no tiene reglas propias, no tiene `domain/`.** `auth` es el
  ejemplo. No se crean carpetas vacias por simetria (eso paso en CRIS: doce
  modulos con `domain/` vacio).
- **Un archivo por tabla, uno por entidad, uno por caso de uso.** En CRIS un solo
  `use_cases.py` llego a 8.000 lineas: no repetirlo es una decision explicita
  ([ADR 0002](docs/adr/0002-un-archivo-por-tabla-y-por-caso-de-uso.md)).
- **Toda la composicion de dependencias vive en `interfaces/http/dependencies.py`**,
  nunca dentro del router.
- **La logica de negocio va en el dominio o en el caso de uso**, nunca en el
  router ni en el repositorio.
- Un modelo nuevo se registra en `app/shared/db/registry.py`.
- SOLID con criterio: nada de abstracciones sin un segundo caso de uso real.
- Funciones pequenas, nombres explicitos, sin codigo muerto ni comentarios que
  repiten lo que dice el codigo. Un comentario explica **por que**, no **que**.
- Errores explicitos: nada de `except` vacios.

## 7. Privacidad y seguridad (DevSecOps)

- **Toda consulta filtra por el dueno de los datos**, y el `owner_id` esta en la
  firma del puerto para que no se pueda olvidar.
- **Toda funcionalidad que lea datos de una persona lleva un test que intenta
  leerlos desde otra cuenta y exige que falle** (`tests/integration/test_privacy.py`).
- Pedir un recurso ajeno responde **404, no 403**.
- Nunca hardcodees secretos: variables de entorno y `.env.example` al dia.
- Valida todo lo que entra: las imagenes se comprueban por firma binaria, no por
  el content-type que declara el cliente.
- Las contrasenas nunca se registran en logs ni se devuelven en una respuesta.
- Antes de anadir una dependencia, justificala y comprueba que este mantenida.
- No ejecutes comandos destructivos (`rm -rf`, `git push --force`,
  `docker compose down -v`, migraciones en produccion) sin confirmacion.

## 8. Base de datos

- **Todo cambio de esquema es una migracion de Alembic.** Nunca SQL suelto.
- Aqui `--autogenerate` **si** sirve: el esquema nace de los modelos (al reves
  que en CRIS). Revisa siempre lo que genera antes de commitear.
- `alembic check` en CI detecta un modelo cambiado sin migracion.
- Clave primaria UUID en todas las tablas.
- Las tablas van al esquema predeterminado de la base. `DB_SCHEMA` solo se usa
  en los tests (`memories_test`), para aislarlos sin otra base de datos.

## 9. Pruebas

- Toda logica nueva lleva test. Un bug arreglado lleva un test que lo reproduce.
- **Unitarias** (`tests/unit/`): dominio y servicios puros, sin base de datos.
- **Integracion** (`tests/integration/`): la API completa contra Postgres real,
  con cache en memoria y almacenamiento en disco. No hacen falta Redis ni MinIO.
- Los tests usan el esquema `memories_test`: no tocan tus datos de desarrollo.

## 10. Git

- Ramas: `feat/…`, `fix/…`, `chore/…`, `docs/…`. **Nunca commits directos a
  `main`.**
- Commits pequenos con Conventional Commits, en espanol:
  `feat(memories): vista calendario por mes`.
- Un commit = un cambio logico, con los tests en verde.
- Todo entra por Pull Request y lo revisa otro integrante.

## 11. Como trabajar conmigo

- Responde en espanol, concreto y breve.
- Si algo es ambiguo, **pregunta antes de asumir**. Si el PRD lo deja abierto,
  registra el supuesto en
  [ADR 0008](docs/adr/0008-supuestos-sobre-pendientes-del-prd.md).
- Dame feedback honesto: si mi enfoque esta mal o desactualizado, dilo y propon
  una alternativa.
- Al terminar una tarea, resume en 2 o 3 lineas que cambio y que falta.
