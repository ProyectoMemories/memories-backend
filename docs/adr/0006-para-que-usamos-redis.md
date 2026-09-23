# ADR 0006 — Para que usamos Redis (y para que no)

- Estado: aceptada
- Fecha: 2026-09-22

## Contexto

Redis no aparece en la lista de requisitos no funcionales. Meterlo "porque si"
anade una pieza que hay que levantar, vigilar y desplegar. La pregunta correcta
no es si nos gusta, sino que problema concreto resuelve hoy.

## Decision

Se incluye, con **dos usos** y ninguno mas:

1. **Almacen de tokens de refresco.** Un JWT es, por definicion, imposible de
   revocar: es valido hasta que vence. Sin un registro externo, "cerrar sesion"
   seria una mentira del cliente. Redis guarda que tokens de refresco siguen
   vivos, lo que permite cerrar sesion de verdad y rotarlos
   (ver [ADR 0003](0003-autenticacion-jwt-hs256.md)).
2. **Rate limiting del login.** Sin un contador compartido, probar contrasenas a
   ciegas sale gratis. El contador tiene que vivir fuera del proceso para
   funcionar con varios workers.

**No** se usa (todavia) para cachear el listado, el calendario ni "revivir": con
el volumen del MVP esas consultas no son un problema, y una cache mal invalidada
crea errores mas raros de depurar que los que evita. Cuando haga falta, el sitio
esta preparado: `CachePort`.

## Consecuencias

- Todo lo que usa Redis pasa por `app/core/cache/port.py`, con dos
  implementaciones: `RedisCache` y `MemoryCache`. Los tests corren con la de
  memoria, asi que **las pruebas no necesitan Redis levantado**.
- Si Redis se cae, la API sigue respondiendo: el rate limiting deja pasar (no se
  bloquea el servicio por una caida de la cache) y la verificacion de sesion
  falla de forma explicita.
- Si Redis se vacia, todo el mundo tiene que iniciar sesion otra vez. Para un MVP
  de tres personas es aceptable; el dia que no lo sea, se cambia
  `CacheRefreshTokenStore` por una tabla y ningun caso de uso se entera.
