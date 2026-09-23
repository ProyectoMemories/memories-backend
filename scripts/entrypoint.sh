#!/bin/sh
# Aplica las migraciones pendientes y arranca lo que venga en CMD.
set -e

echo "[entrypoint] aplicando migraciones..."
intentos=0
until alembic upgrade head; do
    intentos=$((intentos + 1))
    if [ "$intentos" -ge 10 ]; then
        echo "[entrypoint] la base de datos no responde tras $intentos intentos" >&2
        exit 1
    fi
    echo "[entrypoint] base de datos no lista, reintento $intentos/10..."
    sleep 3
done

echo "[entrypoint] migraciones al dia. Arrancando: $*"
exec "$@"
