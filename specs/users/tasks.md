# Spec: users — Tareas

Rama: `feat/users-me`. Un commit por tarea; `/check` en verde antes de cada
commit.

## U1 · Ver mi perfil (`GET /api/v1/users/me`)

- [x] Estructura del módulo `users` y contratos de import-linter (capas, entidades puras, casos de uso sin HTTP ni SQL, frontera con `auth`) · `lint-imports` en verde
- [x] `Profile` (entidad) y `GetMyProfile` con el puerto `ProfileGateway` · tests del interactor con un doble
- [x] `ProfileRecord` y `SqlProfileGateway` sobre `app_user` · test contra PostgreSQL
- [x] Controller `GET /api/v1/users/me` con `CurrentUser`, presenter y composición en `main.py` · tests de la API, incluido "dos cuentas, cada una ve solo lo suyo"
- [x] README y guía del backend en Drive: endpoint nuevo y cómo probarlo
- [x] Prueba manual en `/docs` contra el Docker local
