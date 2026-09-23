# Memories — resumen del producto

Resumen del PRD v3.0 (22/09/2026, borrador) para tenerlo a mano al programar.
**El documento original manda**; esto es un extracto.

## Que es

Un espacio privado donde una persona conserva los momentos que considera
importantes y vuelve a ellos con el tiempo. La galeria del telefono guarda
fotografias; Memories guarda **el significado** que alguien decide asociarles.

## El problema

Conservar las fotografias no es conservar el significado de los momentos. Con el
tiempo se olvida por que fue importante, que pasaba o quien estaba.

## La experiencia central

1. Elegir fotografias que ya estan en el telefono.
2. Anadir el contexto del momento.
3. Guardarlo como recuerdo.
4. Volver a descubrirlo mas adelante.

## El recuerdo (unidad central)

| Elemento | Obligatorio | En el codigo |
|---|---|---|
| Fotografias | Si, al menos una | `Memory.photos` |
| Titulo | Si (supuesto, P16) | `Memory.title` |
| Fecha del momento | Si (supuesto, P16) | `Memory.moment_date` |
| Descripcion | No | `Memory.description` |
| Fecha de creacion | Automatica | `Memory.created_at` |
| Ubicacion | Por decidir (P14) | **no implementado** |

## Capacidades del MVP

| Codigo | Capacidad | Estado |
|---|---|---|
| CP-01 | Crear un recuerdo | implementada |
| CP-02 | Anadir contexto | implementada |
| CP-03 | Consultar recuerdos | implementada |
| CP-04 | Editar y eliminar | implementada |
| CP-05 | Revivir recuerdos | implementada (version provisional, P15) |
| CP-06 | Privacidad por defecto | implementada |
| CP-07 | Compartir un album | **no implementada** (condicional, P17) |
| CP-08 | Vista calendario | implementada |

## Principios (y como se traducen al codigo)

| Principio del PRD | Como se ve en el backend |
|---|---|
| El usuario decide | Nada se crea solo. No hay importacion automatica |
| La IA no es una dependencia | No hay ninguna llamada a modelos ni servicios de IA |
| No es una galeria | La fotografia no existe sin recuerdo que le de sentido |
| Privacidad por defecto | `owner_id` en todos los puertos; 404 ante lo ajeno |
| Terminar antes que ampliar | Lo que no esta en el PRD no se construye |

## Fuera del alcance

IA de cualquier tipo, integraciones con Google Photos o iCloud, video y audio,
funciones sociales (amigos, likes, comentarios, perfiles publicos) y todo lo
comercial (suscripciones, publicidad, PDF, libros).

## Pendientes que afectan al codigo

P13 (maximo de fotos), P14 (ubicacion), P15 (mecanismo de revivir),
P16 (campos obligatorios y fechas aproximadas), P17 (que es un album),
P18 (criterio para retirar el album).

Lo que se ha supuesto y donde se cambia:
[ADR 0008](../adr/0008-supuestos-sobre-pendientes-del-prd.md).
