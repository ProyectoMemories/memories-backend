---
description: Ejecuta en bucle todas las tareas pendientes de specs/<feature>/tasks.md y abre el PR
argument-hint: <feature>
---
Feature: **$ARGUMENTS**

Fase: Implementación.

1. Comprueba que `specs/$ARGUMENTS/requirements.md` diga `Estado: aprobado`. Si no, detente y avisa.
2. Lee en Drive las decisiones del 01 que cita la spec. Compara contra el 01, no contra un resumen.
3. Por cada tarea sin `[x]` de `tasks.md`, en orden:
   a. Escribe primero el test y luego el código. Consulta con Context7 las APIs que todavía no estén en el repo.
   b. Corre /check hasta que esté en verde.
   c. Marca la tarea con `[x]` y haz un commit (Conventional Commits, en español).
4. Detente y pregunta solo si: /check sigue en rojo después de 3 intentos, la tarea necesita una decisión que no está en el 01 o la spec, o el código tiene que desviarse de la spec. Cuando el equipo responda, actualiza la spec antes de seguir.
5. Al terminar todas las tareas, corre el subagente reviewer y corrige los bloqueantes.
6. Haz push de la rama y abre el PR con gh. En la descripción: qué cambió y por qué, en 3 a 5 líneas por tarea, y lo que dijo el reviewer. No lo fusiones.
