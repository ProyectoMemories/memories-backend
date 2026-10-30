# Qué cambia

<!-- Una o dos líneas. Cita el spec y los IDs de Drive que cubre (RF, RN, D). -->

## Spec

- [ ] Existe `specs/<feature>/` y está actualizado
- [ ] Las tareas cerradas están marcadas `[x]` en `tasks.md`

## Revisión propia (D61: nadie más aprueba, así que revisa tú)

- [ ] Leí el diff completo, archivo por archivo
- [ ] `ruff check . && ruff format --check .`
- [ ] `pytest` en verde
- [ ] Si toca el esquema: hay una migración de Alembic nueva, revisada a mano
- [ ] Si lee datos de una persona: hay un test que intenta leerlos desde otra
      cuenta y recibe 404 (D60)
- [ ] No hay secretos, `.env` ni archivos personales en el diff

## Notas

<!-- Decisiones discutibles, deuda asumida, lo que quedó fuera -->
