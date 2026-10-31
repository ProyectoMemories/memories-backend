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
| Requisitos (RF-xx, RNF-xx) | Lista de requisitos |
| Modelo físico vigente | memories-physical-v1.4.sql |

- **No copies esos documentos al repositorio.** Un spec cita los IDs (RF-01,
  RN-67, D56) en lugar de repetir su texto.
- Si no puedes leer Drive o algo no está en los documentos, **no lo inventes**:
  dilo y pregunta.
- Si una tarea contradice una decisión o una regla registrada, avisa antes de
  seguir.

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
| Calidad | pytest, ruff, GitHub Actions (D48) |

**No hay Redis** en este proyecto: las sesiones viven en PostgreSQL (D56).

## 4. Comandos

Se completan a medida que entran los PR de `chore/docker-compose`,
`feat/app-skeleton` y `feat/db-initial-migration`. No inventes comandos que el
repositorio todavía no tiene.

## 5. Estructura (respétala)

```
CLAUDE.md / CLAUDE.local.md   memoria del proyecto / personal (local, en .gitignore)
README.md                     cómo levantar y probar el proyecto (D55)
.github/                      CI y plantilla de PR
specs/<feature>/              requirements.md, design.md, tasks.md
alembic/versions/             migraciones
tests/                        espejo de app/
app/
├── main.py                   app FastAPI y montaje de routers
├── config.py                 configuración por variables de entorno
├── storage/                  puerto de almacenamiento + adaptador S3
└── modules/<modulo>/         auth, users, albums, memories
    ├── router.py             HTTP: valida entrada, llama al servicio
    ├── service.py            reglas de negocio, sin FastAPI
    ├── repository.py         único que toca la base de datos
    ├── models.py             modelos SQLAlchemy
    └── schemas.py            esquemas Pydantic de entrada y salida
```

- No crees carpetas ni archivos de primer nivel sin preguntar.
- Nunca subas `.env`, `CLAUDE.local.md` ni `.claude/settings.local.json`.
- Nombres de archivos, carpetas, tablas, clases y variables **en inglés**, sin
  tildes (D31). Comentarios, specs, commits y mensajes para la persona, **en
  español**.

---

## 6. Flujo obligatorio: Spec-Driven Development

1. **Sin spec no hay código.** Antes de implementar, comprueba que existe
   `specs/<feature>/`. Si no existe, créala y **detente** para que la revisemos.
2. **requirements.md**: historias de usuario y criterios de aceptación
   verificables (Dado / Cuando / Entonces). Cita los RF, RN y D de Drive.
3. **design.md**: contratos de la API, tablas que usa (del modelo v1.4), capas
   que se tocan y riesgos. Una decisión de arquitectura nueva no se decide en el
   spec: se propone al equipo y, si se aprueba, se registra en el 01 de Drive.
4. **tasks.md**: tareas pequeñas, ordenadas por dependencia, cada una con su
   test. Se marcan `[x]` al terminar.
5. Implementa **una tarea a la vez**. Antes de cerrarla: tests y lint en verde.
6. Si la implementación se desvía del spec, **actualiza el spec primero** y
   avisa.

## 7. Reglas de arquitectura

Monolito modular (D13): cada módulo sigue `router → service → repository`.

- El **servicio** tiene las reglas de negocio y no importa FastAPI.
- Solo el **repositorio** accede a la base de datos.
- Un módulo **no usa el repositorio de otro**: si necesita algo, llama a su
  servicio.
- La lógica de negocio nunca va en el router ni en el repositorio.
- SOLID con criterio: nada de abstracciones sin un segundo caso de uso real.
- Funciones pequeñas, nombres explícitos, sin código muerto. Un comentario
  explica **por qué**, no **qué**.
- Errores explícitos: nada de `except` vacíos.

## 8. Base de datos

- El esquema sale de **memories-physical-v1.4.sql** (D53, D56). La migración
  `0001` se escribe **a mano** desde ese archivo: autogenerate no reproduce los
  triggers, `ON DELETE SET NULL (columna)` ni todos los CHECK.
- Después de la `0001`, **todo cambio de esquema es una migración nueva** de
  Alembic, revisada a mano. Nunca SQL suelto contra la base.
- Ids UUIDv7 generados en el backend, **sin DEFAULT** en la columna (D41).
- Todo timestamp es `timestamptz` en UTC.
- Nombres de restricciones: `pk_`, `fk_`, `uq_`, `ck_`, `ix_` + tabla + detalle,
  igual que en el modelo físico.
- Las reglas que la base **no** impone (listadas al final del `.sql`) viven en
  el servicio y cada una tiene su test: edad mínima, 0 a 10 fotos por recuerdo,
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
- En cada petición se revisa que la cuenta siga activa.
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
- Unitarias para los servicios; de integración contra PostgreSQL 18 real para
  la API y las migraciones.

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

## 13. Cómo trabajar conmigo

- Responde en español, concreto y breve.
- Si algo es ambiguo, **pregunta antes de asumir**.
- Dame feedback honesto: si mi enfoque está mal o desactualizado, dilo y propón
  una alternativa.
- Al terminar una tarea, resume en 2 o 3 líneas qué cambió y qué falta.
