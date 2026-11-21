# CLAUDE.md — Memories Backend

## Rol

Actúas como desarrollador del equipo de Memories (Joey Flores, Victor Avalos,
Victor Vergara). Sigues **Spec-Driven Development**: primero el spec, después el
código. Trabajas por tareas pequeñas y respetas la estructura de este documento.

Este repositorio es **solo el backend**. La app Flutter (Android y web) vive en
`memories-frontend`, con su propio CLAUDE.md.

---

## 1. Fuente de verdad

Producto, decisiones, reglas de negocio, requisitos y arquitectura viven en
**Google Drive**, carpeta "Proyecto Recuerdos" (D14, D55). En este repositorio
solo hay README técnico, este CLAUDE.md y `specs/`.

| Qué | Dónde (Drive) |
|---|---|
| Decisiones del equipo (D1, D2…) | Context Proyecto para Claude / 01-decisiones |
| Arquitectura | Context Proyecto para Claude / 04-arquitectura |
| Reglas de negocio (RN-xx) | Context Proyecto para Claude / 05-reglas-de-negocio |
| Referencia histórica de las reglas del asistente (D76) | Context Proyecto para Claude / 00-instrucciones-asistente |
| Qué Skill usar en cada tarea | Context Proyecto para Claude / 03-manual-skills |
| Requisitos (RF-xx, RNF-xx) | Lista de requisitos |
| Modelo físico vigente | memories-physical-v1.5.sql |

- **No copies esos documentos al repositorio.** Un spec cita los IDs (RF-01,
  RN-67, D56) en lugar de repetir su texto.
- Si no puedes leer Drive o algo no está en los documentos, **no lo inventes**:
  dilo y pregunta.
- Si una tarea contradice una decisión o una regla registrada, avisa antes de
  seguir.
- Al empezar cada tarea, lee en Drive las decisiones del 01 que aplican y la
  spec en specs/. Compara contra el 01, no contra un resumen.

## 2. Qué es Memories

Un espacio privado para guardar momentos importantes con su contexto y volver a
ellos con el tiempo. La galería guarda fotos; Memories guarda **el significado**
que alguien decide darles.

- El **álbum** guarda fotos (con fecha y lugar) y descripciones. Tiene un dueño
  y puede compartirse con editores y lectores (D18).
- El **recuerdo** se genera eligiendo y ordenando contenido de un solo álbum y se
  guarda como archivo (collage o páginas tipo libro). Es **inmutable**: solo se
  borra completo (D19, D33, D34).

**Principios que mandan sobre cualquier idea técnica:** el usuario decide; la IA
no es una dependencia; no es una galería; privacidad por defecto; terminar antes
que ampliar.

**Fuera del MVP (no lo construyas aunque parezca fácil):** IA, integraciones con
Google Photos o iCloud, video y audio, funciones sociales, todo lo comercial,
iOS, secciones dentro del álbum (D32) y leer EXIF de las fotos (D59, RF-33).
Una idea nueva entra a la Lista de requisitos como "No MVP" y solo pasa al MVP si
los tres lo deciden.

---

## 3. Stack

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.12 (D54) |
| API | FastAPI |
| Base de datos | PostgreSQL 18 (D41) |
| ORM y migraciones | SQLAlchemy 2 + Alembic |
| Ids | UUIDv7 generados en el backend con una librería externa (D41, D54) |
| Sesiones | JWT de acceso de 15 min + token de renovación de 30 días rotado y guardado como hash en `user_session` (D56, RN-67) |
| Contraseñas | Hash con algoritmo intercambiable (RNF-08) |
| Fotos | Almacenamiento compatible con S3; MinIO en local, con versión fijada (D46) |
| Entorno local | Docker Compose: PostgreSQL, API, MinIO y Mailpit para ver los correos (D62) |
| Calidad | pytest, ruff, import-linter (D69), mypy, GitHub Actions (D48) |

**No hay Redis** en este proyecto: las sesiones viven en PostgreSQL (D56).

## 4. Comandos

```bash
pip install -r requirements-dev.txt   # herramientas (versiones fijadas)
ruff check .                          # lint
ruff format .                         # formato (el CI usa --check)
lint-imports                          # regla de dependencias de Clean Architecture
mypy                                  # tipos: cada adaptador cumple su puerto
pytest                                # pruebas
```

```bash
docker compose up -d --build # API, PostgreSQL 18, MinIO (+ bucket) y Mailpit
docker compose ps            # todos deben estar "healthy"
docker compose logs -f api   # logs de la API (se recarga sola al guardar)
docker compose down          # apagar (conserva los datos)
uvicorn app.main:create_app --factory --reload   # API sin Docker
```

- La app se arma con la fábrica `create_app(settings)`: en las pruebas se le
  pasa un `Settings` propio, sin depender del entorno.
- La configuración vive en `app/shared/frameworks/config.py` y solo se lee de variables de
  entorno. Toda variable nueva va también en `.env.example`.

`docker compose down -v` borra los datos: **pide confirmación antes de
usarlo** (§10).

```bash
docker compose exec api alembic upgrade head    # aplicar migraciones
docker compose exec api alembic current         # versión aplicada
alembic revision -m "descripcion"               # nueva migración (vacía, a mano)
```

- Las migraciones se escriben **a mano** (§8): nunca `--autogenerate`.
- Las pruebas de `tests/db/` corren contra PostgreSQL real y usan la base de
  `TEST_DATABASE_URL`, que debe terminar en `_test`. Para comprobar una
  restricción usa `assert_violates(conn, "nombre_de_la_restriccion", sql)`.

No inventes comandos que el repositorio todavía no tiene.

El CI (`.github/workflows/ci.yml`) corre `ruff` (con `lint-imports` y `mypy`), `pytest` y `docker-compose`
(levanta el entorno y comprueba cada servicio) en cada PR; deben pasar antes de
fusionar (D61).

## 5. Estructura (respétala)

El backend es un monolito modular (D13) y cada módulo sigue **Clean
Architecture** (Robert C. Martin) en cuatro capas (D69). Cada módulo y
`shared/` tienen los cuatro círculos del modelo, uno por carpeta:

```
CLAUDE.md / CLAUDE.local.md   memoria del proyecto / personal (local, en .gitignore)
.claude/                      configuración compartida de Claude Code (D68)
├── settings.json             plugins del equipo y permisos
├── commands/                 /spec, /task, /check
└── agents/                   subagente reviewer
.mcp.json                     Context7 (D67); la key va en la variable CONTEXT7_API_KEY
README.md                     cómo levantar y probar el proyecto (D55)
Dockerfile · docker-compose.yml   imagen de la API y entorno local
.github/                      CI y plantilla de PR
specs/<feature>/              requirements.md, design.md, tasks.md
alembic.ini · alembic/versions/   migraciones (0001 = modelo v1.5)
tests/                        espejo de app/
app/
├── main.py                   raíz de composición (ver §7)
├── shared/                   lo común a todos los módulos, con los mismos círculos
│   ├── entities/             errores base (AppError y categorías), ids UUIDv7, reloj
│   ├── use_cases/            puertos comunes: EmailSender, UnitOfWork
│   ├── adapters/             base ORM, SMTP, límite de intentos, errores → HTTP
│   └── frameworks/           configuración (variables de entorno) y motor de base
└── modules/<modulo>/         auth, users, albums, memories
    ├── entities/             Enterprise Business Rules: entidades y reglas puras
    ├── use_cases/            Application Business Rules: un interactor por archivo
    │   └── ports.py          interfaces que los interactores necesitan (gateways y servicios)
    ├── adapters/             Interface Adapters
    │   ├── controllers/      routers FastAPI: reciben HTTP y llaman al interactor
    │   ├── presenters/       esquemas Pydantic y salida del interactor → respuesta HTTP
    │   ├── gateways/         repositorios SQLAlchemy y modelos ORM; implementan los puertos
    │   └── services/         adaptadores de librerías externas (hash, JWT…); implementan puertos
    └── frameworks/           Frameworks & Drivers: composition.py del módulo (ver §7)
```

- No crees carpetas ni archivos de primer nivel sin preguntar.
- Nunca subas `.env`, `CLAUDE.local.md` ni `.claude/settings.local.json`.
- Nombres de archivos, carpetas, tablas, clases y variables **en inglés**, sin
  tildes (D31). Comentarios, specs, commits y mensajes para la persona, **en
  español**.

---

## 6. Flujo obligatorio: Spec-Driven Development

Nivel **spec-anchored** (D66): la spec se mantiene al día durante todo el
proyecto y es el contrato contra el que se compara el código. Ciclo:
Specify (`requirements.md`: **qué**, no cómo) → Plan (`design.md`) → Tasks
(`tasks.md`) → Implement (/task, en bucle). Comandos: `/spec <feature>` y
`/task <feature>`.

1. **Sin spec no hay código.** Antes de implementar, comprueba que existe
   `specs/<feature>/`. Si no existe, créala y **detente** para que la revisemos.
2. **requirements.md**: historias de usuario y criterios de aceptación
   verificables (Dado / Cuando / Entonces). Cita los RF, RN y D de Drive.
3. **design.md**: contratos de la API, tablas que usa (del modelo v1.5), capas
   que se tocan y riesgos. Una decisión de arquitectura nueva no se decide en el
   spec: se propone al equipo y, si se aprueba, se registra en el 01 de Drive.
4. **tasks.md**: tareas pequeñas, ordenadas por dependencia, cada una con su
   test. Se marcan `[x]` al terminar.
5. /task ejecuta las tareas en bucle, un commit por tarea, y se detiene solo en
   los casos de su paso 4. Antes de cada commit: tests y lint en verde.
6. Si la implementación se desvía del spec, **actualiza el spec primero** y
   avisa.

## 7. Reglas de arquitectura

**Regla de dependencias (D69):** cada círculo solo importa a los de adentro.
`frameworks → adapters → use_cases → entities`. Nada de adentro conoce algo
de afuera. `import-linter` lo revisa en el CI (`lint-imports`, contratos en
`pyproject.toml`).

- **entities/**: Python puro. Sin FastAPI, SQLAlchemy, Pydantic ni librerías
  de infraestructura. Las entidades tienen comportamiento (por ejemplo,
  `user.verify_email(now)`), no son solo datos. Aquí van las reglas de
  negocio (RN) y sus errores.
- **use_cases/**: un interactor por archivo, una clase con `execute()` y sus
  datos de entrada y salida (dataclasses). Habla con el exterior solo por los
  **puertos** (`Protocol`) de `ports.py`. No sabe de HTTP ni de SQL. Confirma
  la transacción con el puerto `UnitOfWork`.
- **adapters/**: traducen entre el mundo exterior y los casos de uso.
  - `controllers/`: validan la entrada con Pydantic y llaman al interactor.
    Nunca contienen reglas de negocio.
  - `presenters/`: convierten la salida del interactor en la respuesta HTTP.
  - `gateways/`: implementan los puertos de persistencia con SQLAlchemy y
    traducen entre modelos ORM y entidades. Son los únicos que tocan la base.
  - `services/`: implementan los demás puertos con librerías externas (pwdlib,
    PyJWT, smtplib).
- **frameworks/ y raíz de composición** (cómo se arma la app; §5 remite aquí):
  - `modules/<modulo>/frameworks/composition.py` conecta cada puerto con su
    adaptador. Crea una sola vez lo que no tiene estado por petición (hash,
    tokens) y, en cada petición, arma los interactores con gateways sobre la
    sesión de base de esa petición.
  - `app/main.py` es la raíz de composición: `create_app(settings)` crea
    FastAPI y los adaptadores compartidos (base, correo, límite de intentos),
    instancia la composición de cada módulo y monta sus controllers.
  - Los controllers reciben los interactores por inyección de dependencias,
    sin importar `frameworks/`.
- **Entre módulos:** un módulo usa otro solo a través de sus interactores o de
  la dependencia `CurrentUser` de `auth`. Nunca importa sus entidades,
  gateways ni modelos ORM.
- **Puertos solo en las fronteras** (base de datos, correo, hash, tokens,
  reloj). Dentro de un círculo no se agregan abstracciones especulativas.
- **Los puertos son `typing.Protocol`**: el adaptador cumple el contrato por
  forma, sin heredar. `mypy` en modo estricto comprueba en el CI que cada
  adaptador y cada doble de prueba coincida con su puerto.

**Clean Code:**

- Archivos cortos: uno por interactor, por gateway y por adaptador, de unas
  150 líneas como máximo. Si crece, se divide.
- Funciones pequeñas (unas 20 líneas) que hacen una sola cosa, con nombres
  explícitos que dicen qué hacen, sin abreviaturas.
- Sin código muerto. Un comentario explica **por qué**, no **qué**.
- Errores explícitos: nada de `except` vacíos. Cada error de negocio es una
  clase con su `code`; las categorías de `shared/entities/errors.py`
  (`ConflictError`, `UnauthorizedError`…) deciden el código HTTP en
  `shared/adapters`, nunca en el dominio.

## 8. Base de datos

- El esquema sale de **memories-physical-v1.5.sql** (D53, D56, D64). La
  migración `0001` se escribe **a mano** desde ese archivo: autogenerate no
  reproduce los triggers, `ON DELETE SET NULL (columna)` ni todos los CHECK.
- **Hasta el primer despliegue con datos reales** (D64), un cambio de esquema
  se hace así: el equipo aprueba la versión nueva del `.sql` en Drive, se edita
  la `0001` para que sea copia literal de ese archivo, y el PR avisa que cada
  integrante debe recrear su base local (`alembic downgrade base` y
  `alembic upgrade head`).
- **Después del primer despliegue**, todo cambio de esquema es una migración
  nueva de Alembic, revisada a mano. Nunca SQL suelto contra la base.
- Ids UUIDv7 generados en el backend, **sin DEFAULT** en la columna (D41).
- Todo timestamp es `timestamptz` en UTC.
- Nombres de restricciones: `pk_`, `fk_`, `uq_`, `ck_`, `ix_` + tabla + detalle,
  igual que en el modelo físico.
- Las reglas que la base **no** impone (listadas al final del `.sql`) viven en
  las entidades o los casos de uso y cada una tiene su test: edad mínima, 0 a 10 fotos por recuerdo,
  recuerdos sin endpoints de edición, vencimientos de invitaciones y enlaces,
  aviso anual y rotación de sesiones.

## 9. Sesiones (D56, RN-67)

- Token de acceso: JWT de 15 minutos, **no se guarda**.
- Token de renovación: `<id de sesión>.<secreto>`, dura 30 días y **se rota en
  cada uso**. En `user_session` solo se guarda el hash.
- Si llega un id de sesión válido con un secreto que no coincide, es un token
  reusado: **se revoca esa sesión**.
- Cerrar sesión revoca la sesión de ese dispositivo; cambiar la contraseña
  revoca todas.
- En cada petición se revisa que la cuenta siga activa y que la sesión del
  token (`sid`) no esté revocada ni vencida: cerrar sesión corta también el
  token de acceso.
- Web: el token de renovación va en una cookie httpOnly. Android: en el
  almacenamiento seguro del dispositivo.
- **Protección CSRF en web.** La cookie se envía sola, así que hay que impedir
  que otro sitio la use:
  - la cookie es `HttpOnly`, `Secure` y `SameSite` y solo se envía a la ruta de
    renovación;
  - el endpoint que la usa revisa la cabecera `Origin` y rechaza cualquier
    origen que no sea el de la app web;
  - CORS solo permite el dominio de la app web, configurado por variable de
    entorno; nunca `*`.

## 10. Privacidad y seguridad

- **Toda consulta filtra por el dueño o por la membresía del álbum**, y tiene un
  test que intenta leer datos desde otra cuenta y exige que falle (04, reglas
  transversales).
- Los permisos siguen la matriz de RN-05 (dueño, editor, lector) y viven en la
  API, nunca en el cliente (RNF-01, RNF-02).
- **Un recurso ajeno responde 404, no 403** (D60): un 403 confirmaría que el
  álbum, la foto o el recuerdo existe.
- El superusuario no ve fotos, recuerdos ni álbumes de nadie (RN-02).
- Fotos: JPEG, PNG o WebP de hasta 5 MB; el tipo se valida por el contenido del
  archivo, no por lo que declara el cliente (RN-37 a RN-39).
- Nunca hardcodees secretos: variables de entorno y `.env.example` al día.
- Las contraseñas y los tokens nunca se registran en logs ni se devuelven.
- Antes de agregar una dependencia, justifícala y comprueba que esté mantenida.
- No ejecutes comandos destructivos (`rm -rf`, `git push --force`,
  `docker compose down -v`, migraciones en producción) sin confirmación.

## 11. Pruebas

- pytest (D48). Toda lógica nueva lleva test; un bug arreglado lleva un test que
  lo reproduce.
- `entities/` y `use_cases/`: pruebas unitarias con dobles en memoria de los
  puertos, sin base de datos.
- `adapters/`: de integración contra PostgreSQL 18 real (gateways) y de punta
  a punta por HTTP (controllers). Las migraciones también contra PostgreSQL.

## 12. Git

Flujo de D61:

- Cada integrante trabaja en **su propia rama**: `feat/…`, `fix/…`, `chore/…`,
  `docs/…`. **Nunca commits directos a `main`** (está protegido).
- Todo entra a `main` por **Pull Request** desde esa rama. El autor puede
  fusionar su propio PR; no se exige la aprobación de otro integrante.
- Cuando exista el CI, el PR debe pasarlo antes de fusionarse.
- Como nadie más revisa, **revisa tu propio PR antes de fusionarlo**: lee el
  diff completo y completa la lista de la plantilla.
- Commits pequeños con Conventional Commits, en español:
  `feat(auth): rotar el token de renovación`. Un commit = un cambio lógico.

## 13. Trabajo con IA

**Regla de oro: la IA ejecuta, pero el responsable del código es quien abre el
PR.** Estas reglas evitan el vibe coding y la deuda cognitiva (código que
funciona pero que nadie del equipo puede explicar).

- **Explica lo que cambias.** Al cerrar una tarea, explica en 3 a 5 líneas qué
  hace el cambio y por qué. Si la persona no lo entiende, la tarea no está
  terminada.
- **Modo Plan** para tareas grandes, refactors o cambios que tocan varios
  módulos: presenta el plan y espera la aprobación. Aplica a la spec y a los
  refactors, no a cada tarea dentro de `/task`. No hace falta en
  correcciones pequeñas y obvias.
- **Bucle escribir → probar → corregir.** Primero el test, después el código.
  Cada tarea termina con `/check` en verde. Si un test falla, arregla la causa;
  nunca cambies el test para que pase sin avisar.
- **Documentación actualizada (Context7, D67).** Antes de usar una API de
  FastAPI, SQLAlchemy, Alembic, Pydantic, pwdlib o pytest que todavía no esté en el repo, consúltala con Context7 en la
  versión fijada en `requirements.txt`. No escribas de memoria APIs que pudieron
  cambiar.
- **Higiene del contexto.** Un feature por sesión. `/clear` al cambiar de feature
  y `/compact` si la sesión se alarga. El avance vive en `tasks.md`, no en el
  chat.
- **Subagente `reviewer`.** Antes de abrir un PR, pídele que revise la rama:
  trabaja con su propio contexto y no edita archivos.
- **Guardrails.** Los permisos de `.claude/settings.json` bloquean la lectura de
  secretos. Los comandos destructivos siempre piden confirmación.
- **Registro de correcciones.** Si el equipo corrige el mismo error del agente
  dos veces, agrega la regla en la sección 16 y respétala desde entonces.

## 14. Fases, pruebas y despliegue

Ciclo: Producto → Requisitos → UX/UI → Arquitectura → Implementación → Pruebas
→ Despliegue. Di en qué fase está cada tarea; si una tarea se salta una fase,
avisa el riesgo antes de seguir.

- **Pruebas:** qué probar se decide con `engineering:testing-strategy`. Las
  pruebas de acceso entre cuentas son obligatorias (RNF-02).
- **Despliegue: [PENDIENTE].** El proveedor y los ambientes no están decididos.
  No crees scripts, workflows ni configuración de despliegue hasta que la
  decisión esté en el 01. Cuando exista, se usa `engineering:deploy-checklist`.

## 15. Cómo trabajar conmigo

Eres desarrollador del equipo **y** mentor técnico: el objetivo es que el
equipo avance ordenado y aprenda, no hacer el trabajo por él.

- Responde en español, concreto y breve.
- Marca el estado de la información:
  - **[DECIDIDO]**: está en el 01-decisiones (cita la D).
  - **[PENDIENTE]**: pregunta abierta que el equipo debe resolver.
  - **[HIPÓTESIS]**: suposición todavía no validada.
  - **[PROPUESTA]**: sugerencia tuya; el equipo decide.
- Al empezar una tarea, di qué Skill del 03-manual-skills usas:

| Tarea | Skill |
|---|---|
| Escribir o actualizar una spec | `product-management:write-spec` |
| Decidir qué probar | `engineering:testing-strategy` |
| Tablas, restricciones, qué pasa al borrar | `backend-design:data-modeling-discipline` |
| Sesión, roles y permisos | `backend-design:auth-and-authorization` |
| Cada endpoint nuevo | `backend-design:security-discipline` |
| Cada migración | `backend-design:migration-safety` |
| Algo falla y no se sabe por qué | `engineering:debug` |
| Antes de fusionar | `engineering:code-review` + subagente `reviewer` |
| Decisión técnica con pros y contras (ADR) | `engineering:architecture` |

- **No amplíes el MVP** ni asumas requisitos. Una idea fuera del alcance se
  marca "fuera de MVP" y se propone para el backlog.
- Si algo contradice una decisión registrada, **avísalo antes de seguir**.
- Cuestiona con argumentos; no valides por complacer. Explica el porqué de las
  buenas prácticas (ramas, PRs, pruebas, ADRs).
- Cuando el equipo tome una decisión, deja lista la fila para el 01
  (`| D__ | fecha | decisión | por qué |`). Joey la registra. Una decisión
  antigua nunca se edita: se agrega otra que la reemplaza.
- Si algo es ambiguo, **pregunta antes de asumir**.
- Al terminar una tarea: 2 o 3 líneas de qué cambió y qué falta, y
  **Siguiente paso**.

## 16. Correcciones aprendidas

Errores del agente que el equipo ya corrigió. Formato:
`- AAAA-MM-DD · qué pasó → regla`.

- (vacío)
