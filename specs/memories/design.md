# Spec: recuerdos — Diseno

## Contratos de la API

| Metodo | Ruta | Cuerpo / parametros | Respuesta |
|---|---|---|---|
| POST | `/api/v1/photos` | multipart `file` | 201 `PhotoResponse` |
| GET | `/api/v1/photos/{id}/raw` | — | 200 imagen |
| DELETE | `/api/v1/photos/{id}` | — | 204 |
| POST | `/api/v1/memories` | `{title, moment_date, photo_ids[], description?}` | 201 `MemoryResponse` |
| GET | `/api/v1/memories` | `page, size, date_from, date_to, q` | 200 lista paginada |
| GET | `/api/v1/memories/calendar` | `year, month` | 200 `{year, month, days[]}` |
| GET | `/api/v1/memories/revive` | — | 200 `{reason, memories[]}` |
| GET | `/api/v1/memories/{id}` | — | 200 `MemoryResponse` |
| PATCH | `/api/v1/memories/{id}` | `{title?, moment_date?, description?, clear_description?}` | 200 `MemoryResponse` |
| DELETE | `/api/v1/memories/{id}` | — | 204 |
| POST | `/api/v1/memories/{id}/photos` | `{photo_ids[]}` | 200 `MemoryResponse` |
| DELETE | `/api/v1/memories/{id}/photos/{photo_id}` | — | 200 `MemoryResponse` |

Las rutas fijas (`/calendar`, `/revive`) se declaran antes que `/{memory_id}`.

`clear_description` existe para distinguir "no toques la descripcion" (campo
ausente) de "borrala" (`true`). Sin ese campo, `null` seria ambiguo.

## Por que la foto se sube antes que el recuerdo

Dos alternativas:

1. **Todo en una peticion** (multipart con campos + archivos). Cumple el
   invariante "al menos una foto" de forma atomica, pero la persona espera a que
   suban todas las fotos despues de escribir, y reintentar significa volver a
   subirlo todo.
2. **Subida previa, asociacion despues** (la elegida). La app sube mientras la
   persona escribe el titulo. El invariante se sigue cumpliendo: el recuerdo se
   crea con `photo_ids` y el dominio exige al menos uno.

Coste asumido: una fotografia subida y nunca asociada se queda huerfana. Hara
falta una limpieza periodica; no esta hecha (ver `docs/arquitectura.md` §8).

## Modelo de datos

`memories`: `id`, `owner_id` → `users.id` (CASCADE), `title` (120),
`moment_date` (date), `description` (text, nulo), `created_at`, `updated_at`.
Indices: `owner_id` y compuesto `(owner_id, moment_date)` — la lista y el
calendario siempre preguntan "mis recuerdos por fecha".

`photos`: `id`, `owner_id` → `users.id` (CASCADE), `memory_id` → `memories.id`
(CASCADE, **nulo**), `storage_key` (unico), `content_type`, `size_bytes`,
`checksum_sha256`, `position`.

Borrar un recuerdo borra sus fotografias por CASCADE; los archivos del
almacenamiento los borra el caso de uso.

## Reparto por capas

| Capa | Que vive aqui |
|---|---|
| `domain/entities` | `Memory` (invariantes), `Photo` (asociacion y orden) |
| `domain/services` | `revive_selector` — la regla de que mostrar al revivir |
| `domain/repositories` | puertos `MemoryRepository` y `PhotoRepository`, **todos con `owner_id`** |
| `application/use_cases` | uno por accion: crear, listar, ver, editar, borrar, subir foto, asociar, quitar, calendario, revivir |
| `application/image_validator.py` | formatos admitidos y firma binaria |
| `application/photo_url_service.py` | URL firmada o, si no hay, el endpoint propio |
| `infrastructure` | `memory_model.py`, `photo_model.py`, mappers y repositorios |
| `interfaces/http` | `memories_router.py`, `photos_router.py`, esquemas, `dependencies.py` |

## Decisiones

- Almacenamiento intercambiable y URLs firmadas:
  [ADR 0005](../../docs/adr/0005-almacenamiento-minio-o-s3.md).
- Supuestos sobre los pendientes del PRD (titulo obligatorio, sin ubicacion,
  maximo de fotos): [ADR 0008](../../docs/adr/0008-supuestos-sobre-pendientes-del-prd.md).

## Riesgos

| Riesgo | Mitigacion |
|---|---|
| Fotografias huerfanas | Pendiente: tarea de limpieza. Ocupan espacio, no rompen nada |
| `ORDER BY random()` en revivir | Suficiente para el MVP; con muchos recuerdos por persona habria que cambiarlo |
| Un archivo que no se borra del bucket | Se registra en el log; la fila si desaparece |
| Alguien sube una imagen enorme | Limite por `MAX_PHOTO_SIZE_MB`, comprobado antes de tocar el almacenamiento |
