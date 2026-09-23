"""Privacidad por defecto (PRD, principio 4).

Regla del proyecto: toda consulta filtra por el dueno de los datos y existe un
test que intenta leer datos de otra persona y exige que falle.
"""

from collections.abc import Awaitable, Callable

from httpx import AsyncClient


async def test_nadie_ve_los_recuerdos_de_otra_persona(
    client: AsyncClient,
    api: str,
    login_as: Callable[..., Awaitable[dict[str, str]]],
    png: bytes,
) -> None:
    victor = await login_as(email="victor@memories.app", display_name="Victor")
    joey = await login_as(
        email="joey@memories.app", display_name="Joey", password="otraClaveSegura2"
    )

    subida = await client.post(
        f"{api}/photos", headers=victor, files={"file": ("foto.png", png, "image/png")}
    )
    creado = await client.post(
        f"{api}/memories",
        headers=victor,
        json={
            "title": "Privado de Victor",
            "moment_date": "2026-02-01",
            "photo_ids": [subida.json()["id"]],
        },
    )
    memory_id = creado.json()["id"]

    # Joey no lo ve en su lista...
    listado = await client.get(f"{api}/memories", headers=joey)
    assert listado.json()["total"] == 0

    # ...ni entrando por su identificador. Responde 404, no 403: un 403
    # confirmaria que ese recuerdo existe.
    detalle = await client.get(f"{api}/memories/{memory_id}", headers=joey)
    assert detalle.status_code == 404

    # ...ni puede editarlo o borrarlo.
    assert (
        await client.patch(f"{api}/memories/{memory_id}", headers=joey, json={"title": "mio"})
    ).status_code == 404
    assert (await client.delete(f"{api}/memories/{memory_id}", headers=joey)).status_code == 404


async def test_no_se_pueden_usar_fotografias_de_otra_persona(
    client: AsyncClient,
    api: str,
    login_as: Callable[..., Awaitable[dict[str, str]]],
    png: bytes,
) -> None:
    victor = await login_as(email="victor@memories.app", display_name="Victor")
    joey = await login_as(
        email="joey@memories.app", display_name="Joey", password="otraClaveSegura2"
    )

    subida = await client.post(
        f"{api}/photos", headers=victor, files={"file": ("foto.png", png, "image/png")}
    )

    response = await client.post(
        f"{api}/memories",
        headers=joey,
        json={
            "title": "Con una foto ajena",
            "moment_date": "2026-02-01",
            "photo_ids": [subida.json()["id"]],
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "photo_not_found"
