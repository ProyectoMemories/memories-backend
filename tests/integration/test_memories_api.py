"""El flujo completo del PRD: subir fotos, crear el recuerdo, verlo, editarlo y borrarlo."""

from datetime import UTC, date, datetime, timedelta

from httpx import AsyncClient


async def subir_foto(client: AsyncClient, api: str, headers: dict[str, str], png: bytes) -> str:
    response = await client.post(
        f"{api}/photos",
        headers=headers,
        files={"file": ("recuerdo.png", png, "image/png")},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def crear_recuerdo(
    client: AsyncClient,
    api: str,
    headers: dict[str, str],
    png: bytes,
    *,
    title: str = "Viaje a Paracas",
    moment_date: date | None = None,
) -> dict:
    photo_id = await subir_foto(client, api, headers, png)
    response = await client.post(
        f"{api}/memories",
        headers=headers,
        json={
            "title": title,
            "moment_date": (moment_date or date(2026, 1, 15)).isoformat(),
            "description": "El dia que vimos los delfines.",
            "photo_ids": [photo_id],
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


async def test_subir_una_foto_devuelve_su_url(
    client: AsyncClient, api: str, auth_headers: dict[str, str], png: bytes
) -> None:
    response = await client.post(
        f"{api}/photos", headers=auth_headers, files={"file": ("foto.png", png, "image/png")}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["url"]
    assert body["memory_id"] is None


async def test_no_se_admite_un_archivo_que_no_es_imagen(
    client: AsyncClient, api: str, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        f"{api}/photos",
        headers=auth_headers,
        files={"file": ("documento.png", b"esto es texto", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_image"


async def test_crear_un_recuerdo_con_sus_fotografias(
    client: AsyncClient, api: str, auth_headers: dict[str, str], png: bytes
) -> None:
    recuerdo = await crear_recuerdo(client, api, auth_headers, png)

    assert recuerdo["title"] == "Viaje a Paracas"
    assert len(recuerdo["photos"]) == 1
    assert recuerdo["photos"][0]["position"] == 0


async def test_un_recuerdo_sin_fotografias_no_se_crea(
    client: AsyncClient, api: str, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        f"{api}/memories",
        headers=auth_headers,
        json={"title": "Sin fotos", "moment_date": "2026-01-15", "photo_ids": []},
    )

    assert response.status_code == 422


async def test_no_se_puede_guardar_un_recuerdo_del_futuro(
    client: AsyncClient, api: str, auth_headers: dict[str, str], png: bytes
) -> None:
    photo_id = await subir_foto(client, api, auth_headers, png)
    manana = datetime.now(tz=UTC).date() + timedelta(days=1)

    response = await client.post(
        f"{api}/memories",
        headers=auth_headers,
        json={
            "title": "Manana",
            "moment_date": manana.isoformat(),
            "photo_ids": [photo_id],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_moment_date"


async def test_listar_y_ver_el_detalle(
    client: AsyncClient, api: str, auth_headers: dict[str, str], png: bytes
) -> None:
    creado = await crear_recuerdo(client, api, auth_headers, png)

    listado = await client.get(f"{api}/memories", headers=auth_headers)
    assert listado.status_code == 200
    assert listado.json()["total"] == 1

    detalle = await client.get(f"{api}/memories/{creado['id']}", headers=auth_headers)
    assert detalle.status_code == 200
    assert detalle.json()["id"] == creado["id"]


async def test_editar_y_borrar_un_recuerdo(
    client: AsyncClient, api: str, auth_headers: dict[str, str], png: bytes
) -> None:
    creado = await crear_recuerdo(client, api, auth_headers, png)

    edicion = await client.patch(
        f"{api}/memories/{creado['id']}",
        headers=auth_headers,
        json={"title": "Paracas con Joey"},
    )
    assert edicion.status_code == 200
    assert edicion.json()["title"] == "Paracas con Joey"

    borrado = await client.delete(f"{api}/memories/{creado['id']}", headers=auth_headers)
    assert borrado.status_code == 204

    assert (
        await client.get(f"{api}/memories/{creado['id']}", headers=auth_headers)
    ).status_code == 404


async def test_no_se_puede_quitar_la_unica_fotografia(
    client: AsyncClient, api: str, auth_headers: dict[str, str], png: bytes
) -> None:
    creado = await crear_recuerdo(client, api, auth_headers, png)
    photo_id = creado["photos"][0]["id"]

    response = await client.delete(
        f"{api}/memories/{creado['id']}/photos/{photo_id}", headers=auth_headers
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "memory_needs_photo"


async def test_el_calendario_cuenta_los_recuerdos_de_cada_dia(
    client: AsyncClient, api: str, auth_headers: dict[str, str], png: bytes
) -> None:
    await crear_recuerdo(client, api, auth_headers, png, moment_date=date(2026, 1, 15))
    await crear_recuerdo(
        client, api, auth_headers, png, title="Otro", moment_date=date(2026, 1, 15)
    )

    response = await client.get(
        f"{api}/memories/calendar", headers=auth_headers, params={"year": 2026, "month": 1}
    )

    assert response.status_code == 200
    dias = response.json()["days"]
    assert dias == [{"day": "2026-01-15", "count": 2}]


async def test_revivir_devuelve_recuerdos_de_este_dia_en_otro_ano(
    client: AsyncClient, api: str, auth_headers: dict[str, str], png: bytes
) -> None:
    hoy = datetime.now(tz=UTC).date()
    mismo_dia_ano_pasado = date(hoy.year - 1, hoy.month, hoy.day)
    await crear_recuerdo(client, api, auth_headers, png, moment_date=mismo_dia_ano_pasado)

    response = await client.get(f"{api}/memories/revive", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["reason"] == "on_this_day"
    assert len(body["memories"]) == 1
