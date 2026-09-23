# ADR 0003 — JWT HS256 con token de refresco rotativo

- Estado: aceptada
- Fecha: 2026-09-22

## Contexto

RNF-08 pide autenticacion por JWT. En CRIS se uso RS256 con un par de claves RSA
en disco, un script para generarlas y un volumen de Docker para conservarlas; y
el token viajaba en una cookie HttpOnly.

Memories tiene una diferencia que lo cambia todo: el cliente es **Flutter para
movil y web con el mismo codigo** (RNF-05). En movil no hay navegador ni cookies:
el patron nativo es `Authorization: Bearer` con el token en el almacen seguro del
sistema.

## Decision

- **HS256** con un unico secreto (`JWT_SECRET_KEY`). El algoritmo es
  configurable (`JWT_ALGORITHM`) por si algun dia hace falta RS256, que solo
  aporta cuando un tercero debe verificar el token sin poder emitirlo.
- **Token de acceso corto** (30 minutos), sin estado, con `sub`, `role`, `type`,
  `jti`, `iat` y `exp`.
- **Token de refresco largo** (30 dias) **con estado en Redis** y **rotacion**:
  cada renovacion invalida el token usado. Si alguien roba uno y lo usa, el
  legitimo deja de funcionar y el robo se nota.
- El transporte es siempre `Authorization: Bearer`, igual en movil y en web.

## Consecuencias

- Un solo camino de autenticacion para las dos plataformas: cero codigo
  condicional por plataforma.
- Sin ficheros de claves, sin volumen, sin script de generacion. Arrancar el
  proyecto es una variable de entorno.
- En web, guardar el token fuera de una cookie HttpOnly es mas expuesto a XSS que
  la solucion de CRIS. Se compensa con un token de acceso corto y rotacion del de
  refresco. Si mas adelante la web pesa mas que el movil, se puede anadir el modo
  cookie sin tocar los casos de uso.
- Autenticar no consulta la base de datos: el rol viaja en el token. Desactivar a
  alguien surte efecto cuando vence su token de acceso (30 minutos como maximo).
- Si Redis se vacia, todo el mundo vuelve a iniciar sesion. Aceptable para el
  MVP; ver [ADR 0006](0006-para-que-usamos-redis.md).
