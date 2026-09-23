# Spec: album compartido — Tareas

**Bloqueado.** No se empieza ninguna tarea hasta que el equipo cierre P17 y P18
(ver [requirements.md](requirements.md)).

## Antes de escribir codigo

- [ ] Decidir P17: que es un album, su relacion con el recuerdo y que pueden
      hacer las personas invitadas
- [ ] Decidir P18: criterio para retirar el album del MVP si se complica
- [ ] Elegir entre la opcion A y la opcion B de [design.md](design.md)
- [ ] Escribir los criterios de aceptacion de HU-01 y HU-02
- [ ] ADR con la decision y sus consecuencias sobre la privacidad

## Cuando se desbloquee (estimacion del orden)

- [ ] Modulo `albums` con sus cuatro capas
- [ ] Entidades `Album` y `AlbumMember` con la regla "solo el dueno invita"
- [ ] Migracion de las tablas nuevas
- [ ] Casos de uso: crear album, invitar, quitar invitado, anadir recuerdo,
      quitar recuerdo, listar albumes, ver album
- [ ] **Ampliar las reglas de lectura de recuerdos** (el punto delicado)
- [ ] Tests de privacidad del album: alguien invitado ve lo que el album expone
      y nada mas; alguien no invitado recibe 404
- [ ] Endpoints y esquemas
