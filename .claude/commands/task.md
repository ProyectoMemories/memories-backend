---
description: Implementa la siguiente tarea pendiente de specs/<feature>/tasks.md con su test
argument-hint: <feature>
---
Feature: **$ARGUMENTS**

Fase: Implementación.

1. Comprueba que `specs/$ARGUMENTS/requirements.md` diga `Estado: aprobado`.
   Si no, **detente** y avisa.
2. Toma **solo** la primera tarea sin `[x]` de `specs/$ARGUMENTS/tasks.md`.
3. Si la tarea es grande o toca varios módulos, presenta un plan y espera la
   aprobación.
4. Escribe primero el test y luego el código. Si usas una API de una librería
   que todavía no está en el repo, consúltala con Context7.
5. Corre las verificaciones de `/check` y corrige hasta que estén en verde.
6. Si el código se desvió de la spec, actualiza la spec primero y avísalo.
7. Marca la tarea con `[x]`, explica en 3 a 5 líneas qué cambió y por qué, y
   propone el mensaje del commit (Conventional Commits, en español).
   **No hagas commit ni push.**
