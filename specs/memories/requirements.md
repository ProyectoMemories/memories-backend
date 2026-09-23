# Spec: recuerdos — Requisitos

- Capacidades del PRD: CP-01, CP-02, CP-03, CP-04, CP-05, CP-06, CP-08
- Estado: implementado

## Contexto

El recuerdo es la unidad central del producto: una o varias fotografias mas el
contexto que las hace significativas. Esta feature cubre el flujo completo del
criterio de aceptacion del MVP (PRD 8.1): crear, conservar entre sesiones,
encontrar, ver, editar y borrar; ademas del calendario y de "revivir".

## Historias de usuario

### HU-01 — Crear un recuerdo (CP-01, CP-02)

> Como persona que acaba de vivir algo importante, quiero elegir una o varias
> fotografias y anadirles el contexto, para no olvidar por que fue importante.

**Criterios de aceptacion**

- Dadas una o mas fotografias ya subidas, un titulo y una fecha,
  cuando creo el recuerdo,
  entonces se guarda y lo recibo con sus fotografias en el orden en que las eligi.
- Dado un recuerdo sin ninguna fotografia, cuando intento crearlo, entonces se
  rechaza: un recuerdo sin fotografia no es un recuerdo.
- Dada una fecha posterior a hoy, cuando intento crearlo, entonces se rechaza.
- Dadas mas fotografias que el maximo configurado, cuando intento crearlo,
  entonces se rechaza indicando el maximo.
- Dada una fotografia de otra persona, cuando intento usarla, entonces se
  responde "no existe" (no se confirma que exista).
- Dada una descripcion en blanco, cuando creo el recuerdo, entonces se guarda sin
  descripcion (no con una cadena vacia).

### HU-02 — Subir fotografias (CP-01)

> Como persona que crea un recuerdo, quiero que mis fotos se vayan subiendo
> mientras escribo, para no esperar al final.

**Criterios de aceptacion**

- Dada una imagen JPEG, PNG o WebP dentro del limite de tamano, cuando la subo,
  entonces recibo su identificador y una URL para verla.
- Dado un archivo que dice ser una imagen pero no lo es, cuando lo subo,
  entonces se rechaza (se comprueba la firma binaria, no el content-type).
- Dada una imagen que pasa del limite de tamano, cuando la subo, entonces se
  rechaza indicando el limite.
- Dada una fotografia subida y todavia sin recuerdo, cuando la descarto,
  entonces se borra tambien del almacenamiento.

### HU-03 — Consultar mis recuerdos (CP-03)

- Dado que tengo recuerdos, cuando pido la lista, entonces los recibo paginados y
  ordenados del momento mas reciente al mas antiguo.
- Dado un rango de fechas o un texto de busqueda, cuando filtro, entonces solo
  recibo los que encajan.
- Dado el identificador de un recuerdo mio, cuando pido el detalle, entonces lo
  recibo con sus fotografias.

### HU-04 — Editar y borrar (CP-04)

- Dado un recuerdo mio, cuando cambio su titulo, fecha o descripcion, entonces se
  guarda y se actualiza `updated_at`.
- Dado un recuerdo con varias fotografias, cuando quito una, entonces desaparece
  del recuerdo, se borra del almacenamiento y las demas se reordenan.
- Dado un recuerdo con una sola fotografia, cuando intento quitarla, entonces se
  rechaza y se me indica que borre el recuerdo entero.
- Dado un recuerdo mio, cuando lo borro, entonces desaparece con todas sus
  fotografias, tambien del almacenamiento.

### HU-05 — Ver mis recuerdos en un calendario (CP-08)

- Dado un mes, cuando pido el calendario, entonces recibo cuantos recuerdos hay
  en cada dia de ese mes (solo el recuento: pintar el calendario no necesita mas).
- Dado un mes sin recuerdos, cuando pido el calendario, entonces recibo una lista
  vacia, no un error.

### HU-06 — Revivir (CP-05)

> Como persona que lleva tiempo usando la app, quiero que me devuelva recuerdos
> del pasado, para volver a ellos sin buscarlos.

**Criterios de aceptacion**

- Dados recuerdos de este mismo dia en anos anteriores, cuando pido revivir,
  entonces recibo esos y el motivo `on_this_day`.
- Dado que no hay ninguno de este dia, cuando pido revivir, entonces recibo una
  seleccion al azar y el motivo `random`.
- Dado que no tengo ningun recuerdo, cuando pido revivir, entonces recibo una
  lista vacia y el motivo `none`.

**Pendiente P15:** el mecanismo definitivo lo decide el equipo. Esta version es
provisional y vive aislada en `domain/services/revive_selector.py`.

### HU-07 — Privacidad (CP-06)

- Dado un recuerdo de otra persona, cuando intento verlo, editarlo o borrarlo,
  entonces recibo 404.
- Dada mi lista de recuerdos, cuando la pido, entonces no aparece ninguno ajeno.

## Fuera de esta feature

Albumes compartidos (P17), ubicacion (P14), fechas aproximadas (P16), video y
audio, y cualquier clasificacion automatica.
