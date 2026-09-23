# ADR 0002 — Un archivo por tabla y un archivo por caso de uso

- Estado: aceptada
- Fecha: 2026-09-22

## Contexto

En CRIS cada modulo tenia un unico `models.py` con todas sus tablas y un unico
`use_cases.py` con toda su logica. El modulo mas grande llego a **19.700 lineas**
repartidas en cuatro archivos, y uno solo de ellos (`services.py` de
notificaciones) paso de 2.500. Consecuencias que sufrimos: conflictos de merge
constantes, imposible encontrar nada, y revisiones de codigo que nadie podia
hacer con criterio.

## Decision

- **Una tabla, un archivo**: `infrastructure/models/<tabla>_model.py`.
- **Un caso de uso, un archivo**: `application/use_cases/<accion>.py`, con una
  sola clase publica y su comando (`dataclass`) si lo necesita.
- **Una entidad, un archivo**: `domain/entities/<entidad>.py`.
- Los repositorios se agrupan por agregado, no por modulo:
  `infrastructure/repositories/sqlalchemy_<agregado>_repository.py`.
- Como nadie importa ya "todos los modelos" de golpe, existe
  `app/shared/db/registry.py`: el unico sitio que los importa todos, para que
  Alembic y los tests vean el metadata completo. **Al crear una tabla hay que
  anadirla ahi.**

## Consecuencias

- Muchos archivos pequenos en vez de pocos enormes. El arbol de carpetas es mas
  largo de leer, pero cada archivo cabe en una pantalla.
- Los conflictos de merge caen casi a cero: dos personas que tocan casos de uso
  distintos ya no escriben en el mismo archivo.
- El nombre del archivo dice que hace: `create_memory.py`, `revive_memories.py`.
- Olvidar el registro de un modelo nuevo rompe las migraciones. Lo detecta
  `alembic check` en CI.
