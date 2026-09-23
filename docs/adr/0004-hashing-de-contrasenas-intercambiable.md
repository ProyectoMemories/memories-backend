# ADR 0004 — Hashing de contrasenas intercambiable

- Estado: aceptada
- Fecha: 2026-09-22

## Contexto

RNF-08 pide bcrypt y, explicitamente, **poder cambiar el algoritmo de hashing**.
Un cambio de algoritmo hecho a lo bruto obliga a que todo el mundo restablezca su
contrasena, porque el hash guardado ya no se puede verificar.

## Decision

`app/core/security/hashing/` con un contrato y dos implementaciones:

- `port.py` — `PasswordHasher`: `identifies`, `hash`, `verify`, `needs_rehash`.
- `bcrypt_hasher.py` y `argon2_hasher.py`.
- `service.py` — `PasswordHashingService`: guarda un algoritmo **principal** (el
  que hashea) y un **registro** de todos los conocidos (los que verifican). Al
  verificar, identifica el algoritmo por el prefijo del propio hash (`$2b$`,
  `$argon2id$`).
- `factory.py` — el unico archivo que se toca para anadir un algoritmo. Lee
  `PASSWORD_HASHING_SCHEME`.

El caso de uso de inicio de sesion pregunta `needs_rehash()` y, si la respuesta
es si, vuelve a hashear la contrasena con el algoritmo vigente y la guarda. Es
decir: **el cambio de algoritmo es una variable de entorno y las contrasenas
migran solas segun la gente entra**.

Se usan las librerias `bcrypt` y `argon2-cffi` directamente, no `passlib`:
passlib no publica version estable desde 2020 y su integracion con bcrypt 4.x da
problemas conocidos.

## Consecuencias

- Cambiar bcrypt por Argon2id no invalida ninguna cuenta ni obliga a avisar a
  nadie.
- Conviven hashes de varios algoritmos en la misma columna. Es correcto: el hash
  lleva escrito con que se genero.
- bcrypt ignora lo que pase de 72 bytes, asi que la politica de contrasenas
  (`domain/value_objects/password.py`) lo rechaza antes en vez de truncar en
  silencio.
- Cambiar solo el coste (`BCRYPT_ROUNDS`) tambien dispara el re-hasheo.
