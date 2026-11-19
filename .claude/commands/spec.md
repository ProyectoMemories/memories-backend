---
description: Crea o actualiza la spec de una feature (SDD) y se detiene para revisión
argument-hint: <feature>
---
Feature: **$ARGUMENTS**

Skill: `product-management:write-spec`. Fase: Requisitos.

1. Lee en Drive lo que la feature necesita: 01-decisiones, 04-arquitectura, 05-reglas-de-negocio y la Lista de requisitos.
2. Si `specs/$ARGUMENTS/` existe, compárala con Drive y propone los cambios.
   Si no existe, créala con `requirements.md`, `design.md` y `tasks.md` según
   la sección 6 del CLAUDE.md. Pon `Estado: borrador` en `requirements.md`.
3. Cita los IDs (RF, RN, D) en lugar de copiar el texto de Drive.
4. Lo que no esté en Drive va como **[PENDIENTE]**: no lo inventes.
5. **No escribas código.** Termina con la lista de [PENDIENTE] y pide la
   revisión del equipo.
