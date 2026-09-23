# Spec: album compartido — Diseno (dos alternativas, sin elegir)

Este documento no propone una solucion: deja las dos opciones sobre la mesa con
sus consecuencias, para que el equipo elija al cerrar P17.

## Opcion A — El album agrupa recuerdos que siguen siendo de su dueno

```
albums            id, owner_id, title, created_at
album_members     album_id, user_id, role (viewer), invited_at
album_memories    album_id, memory_id, added_by, added_at
```

- Un recuerdo puede estar en varios albumes y sigue perteneciendo a quien lo creo.
- Compartir es anadir una fila; dejar de compartir es quitarla.
- Cada persona aporta **sus** recuerdos al album comun.

**A favor:** no cambia nada de lo ya construido; la propiedad del recuerdo sigue
siendo una sola; quitar un recuerdo del album no lo borra.

**En contra:** la regla de lectura deja de ser "es mio" y pasa a ser "es mio **o**
esta en un album del que soy miembro". Eso toca `MemoryRepository`: cada consulta
necesitaria tambien el contexto del album. Es el cambio con mas riesgo de
filtrar datos por descuido, y por eso exige tests de privacidad nuevos.

## Opcion B — El album es un espacio aparte

```
albums            id, owner_id, title
album_members     album_id, user_id, role
album_entries     id, album_id, author_id, title, moment_date, description
album_photos      id, album_entry_id, storage_key, ...
```

- Lo que se comparte se **copia** al album; el recuerdo original no se toca.

**A favor:** los recuerdos privados no cambian en absoluto; la privacidad
existente se queda como esta, con su regla de un solo dueno.

**En contra:** duplica contenido y almacenamiento; editar el recuerdo no
actualiza lo compartido; casi todo el modulo de recuerdos se repite.

## Recomendacion tecnica (no es la decision de producto)

La **opcion A** encaja mejor con lo construido y con el principio "no es una
galeria": el album agrupa significado, no copia archivos. El precio es concreto y
hay que aceptarlo con los ojos abiertos: **la privacidad deja de ser una sola
regla**. Si se elige A, la condicion de entrada es ampliar
`tests/integration/test_privacy.py` con el caso "persona invitada ve solo lo que
el album expone, y nada mas de ese dueno".

## Impacto en la arquitectura (si se aprueba)

- Modulo nuevo `app/modules/albums/` con sus cuatro capas.
- `albums` necesitaria leer recuerdos: lo haria a traves del **puerto** de
  `memories`, nunca de su infraestructura (regla verificada por `lint-imports`).
- Endpoints previstos: `POST /albums`, `GET /albums`, `GET /albums/{id}`,
  `POST /albums/{id}/members`, `DELETE /albums/{id}/members/{user_id}`,
  `POST /albums/{id}/memories`, `DELETE /albums/{id}/memories/{memory_id}`.
- Una migracion nueva; ninguna tabla existente cambia en la opcion A.
