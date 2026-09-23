# Que cambia

<!-- Una o dos lineas. Si hay spec, enlazalo: specs/<feature>/ -->

## Spec

- [ ] Existe `specs/<feature>/` y esta actualizado
- [ ] Las tareas cerradas estan marcadas `[x]` en `tasks.md`

## Comprobaciones

- [ ] `ruff check . && ruff format .`
- [ ] `mypy app`
- [ ] `pytest` en verde
- [ ] Si toca el esquema: hay migracion de Alembic y `alembic check` pasa
- [ ] Si toca datos de una persona: hay un test que intenta leerlos desde otra cuenta y falla

## Notas para quien revisa

<!-- Decisiones discutibles, deuda asumida, lo que quedo fuera -->
