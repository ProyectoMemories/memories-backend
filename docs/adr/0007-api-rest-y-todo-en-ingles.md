# ADR 0007 — API REST y codigo en ingles

- Estado: aceptada
- Fecha: 2026-09-22

## Contexto

CRIS uso rutas verbales (`POST /companies/create`, `GET /fase-i/..._get`) y una
mezcla deliberada de idiomas: rutas en ingles, modelo de datos y logica en
espanol (`evaluacion_linea_base`, `orden_compra`). Funciono, pero obligaba a
recordar en que idioma estaba cada cosa y a inventar el verbo de cada endpoint.

Memories empieza de cero y tiene un cliente Flutter que consumira el OpenAPI.

## Decision

- **Rutas REST**: el recurso en la ruta y la accion en el metodo HTTP.
  `POST /memories`, `GET /memories/{id}`, `PATCH /memories/{id}`,
  `DELETE /memories/{id}/photos/{photo_id}`. Las consultas que no son un recurso
  se quedan como sub-rutas de lectura: `GET /memories/calendar`,
  `GET /memories/revive`.
- **Todo el codigo en ingles**: nombres de tablas, columnas, clases, funciones,
  variables y rutas. Sin tildes ni caracteres especiales en nombres de archivos y
  carpetas.
- **Comentarios, documentacion, mensajes de commit y textos de la interfaz en
  espanol**, que es el idioma del equipo y de quien usa la aplicacion. Los
  mensajes de error que ve la persona van en espanol; los codigos de error que
  consume el cliente (`memory_not_found`) van en ingles.

## Consecuencias

- El cliente Dart que se genere o se escriba a partir del OpenAPI sale con
  nombres coherentes, sin traducir a medias.
- Un endpoint nuevo no necesita decidir su verbo: lo dice el metodo HTTP.
- Quien venga de CRIS tiene que cambiar el habito. Es un coste unico y pequeno.
- Todas las respuestas de error comparten forma
  (`{"error": {"code", "message", "details", "request_id"}}`), asi que el cliente
  las trata en un solo sitio.
