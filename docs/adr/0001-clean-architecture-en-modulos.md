# ADR 0001 — Clean Architecture por modulos

- Estado: aceptada
- Fecha: 2026-09-22

## Contexto

Memories es un monolito modular (RNF-07) con Clean Architecture. El equipo ya
construyo CRIS con esa misma idea y el resultado fue a medias: las carpetas
`domain/` existian en los doce modulos y estaban **vacias en todos**. Las
entidades eran modelos de SQLAlchemy, los casos de uso importaban repositorios
concretos y, con el tiempo, unos modulos empezaron a importar la infraestructura
de otros. La estructura tenia el nombre de Clean Architecture pero no su
propiedad util: poder cambiar la base de datos, el framework o el almacenamiento
sin tocar las reglas de negocio.

## Decision

Cuatro capas por modulo, con la regla de dependencia apuntando siempre hacia
adentro:

```
interfaces  →  infrastructure  →  application  →  domain
```

- **domain**: entidades, objetos de valor, errores de negocio y los *puertos*
  (Protocol) de los repositorios. Python puro: no importa FastAPI, SQLAlchemy,
  Pydantic, Redis ni boto3.
- **application**: un caso de uso por archivo. Recibe puertos, nunca clases
  concretas. Puede usar los puertos de `app/core` (almacenamiento, cache), que
  tambien son abstracciones.
- **infrastructure**: modelos de SQLAlchemy, repositorios que implementan los
  puertos y mappers entre fila y entidad.
- **interfaces**: esquemas de Pydantic, routers de FastAPI y `dependencies.py`,
  donde se compone todo.

Dos reglas mas:

1. **Un modulo no importa la infraestructura de otro.** Si necesita algo, usa su
   dominio (puertos, entidades) o la composicion publica de su `dependencies.py`.
2. **Si un modulo no tiene reglas propias, no tiene `domain/`.** `auth` es el
   ejemplo: orquesta el dominio de usuarios con los servicios de seguridad, asi
   que no se le crea una carpeta vacia "por simetria".

Las tres reglas se verifican en CI con `import-linter` (`lint-imports`), no con
buena voluntad.

## Consecuencias

- Los casos de uso se prueban sin base de datos.
- Aparecen los mappers entidad ↔ modelo: codigo extra que en un CRUD sencillo
  se siente burocratico. Es el precio, y se paga en un solo archivo por modulo.
- Cambiar de ORM o de almacenamiento no toca `domain/` ni `application/`.
- Si alguien rompe la regla de dependencia, el pipeline falla y se ve en el PR,
  no seis meses despues.
