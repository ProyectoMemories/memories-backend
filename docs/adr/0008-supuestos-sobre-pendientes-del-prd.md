# ADR 0008 — Supuestos sobre los pendientes del PRD

- Estado: provisional (se revisa cuando el equipo cierre cada pendiente)
- Fecha: 2026-09-22

## Contexto

El PRD v3.0 esta en borrador y deja abiertos seis temas (Anexo A). El codigo no
puede esperar a todos, pero tampoco debe inventar producto por su cuenta. Este
ADR deja por escrito que se ha supuesto, donde vive cada supuesto y que hay que
tocar cuando se decida de verdad.

## Decision

| Ref. | Tema | Supuesto en el codigo | Donde se cambia |
|---|---|---|---|
| P16 | Informacion obligatoria al crear | `title` y `moment_date` son obligatorios; `description` opcional | `domain/entities/memory.py` |
| P16 | Fechas aproximadas | No se admiten: `moment_date` es una fecha exacta y no puede ser futura | `domain/entities/memory.py` |
| P13 | Maximo de fotografias | Configurable, 10 por defecto (`MAX_PHOTOS_PER_MEMORY`) | `.env` |
| P14 | Ubicacion | **No** forma parte del recuerdo. No hay columna | migracion nueva + entidad |
| P15 | Mecanismo de revivir | "En este dia" de anos anteriores; si no hay, seleccion al azar | `domain/services/revive_selector.py` |
| P17 | Que es un album | **Sin implementar.** Ver `specs/albums/` | modulo nuevo |
| P18 | Criterio para retirar el album | Decision del equipo, no del codigo | — |

## Consecuencias

- Cada supuesto esta aislado en un solo archivo, a proposito: cerrarlo no obliga
  a buscar por todo el repositorio.
- **El album compartido no se ha construido.** El PRD dice que su definicion es
  necesaria para aprobar el propio documento (P17), y no estaba claro si un
  recuerdo pertenece a un album, si los invitados pueden anadir recuerdos ni que
  ven exactamente. Implementarlo habria sido inventar producto. En
  `specs/albums/` estan las dos alternativas de modelo con sus consecuencias,
  listas para que el equipo elija.
- Anadir la ubicacion mas adelante es una migracion y dos campos, no un rediseno.
