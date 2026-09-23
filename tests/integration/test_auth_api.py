"""Registro, inicio de sesion, renovacion y cierre de sesion."""

from collections.abc import Awaitable, Callable

from httpx import AsyncClient

CUENTA = {
    "email": "victor@memories.app",
    "display_name": "Victor",
    "password": "unaClaveSegura1",
}


async def test_registrar_devuelve_la_cuenta_sin_la_contrasena(
    client: AsyncClient, api: str
) -> None:
    response = await client.post(f"{api}/auth/register", json=CUENTA)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == CUENTA["email"]
    assert body["role"] == "user"
    assert "password" not in body
    assert "password_hash" not in body


async def test_no_se_puede_registrar_dos_veces_el_mismo_correo(
    client: AsyncClient, api: str
) -> None:
    await client.post(f"{api}/auth/register", json=CUENTA)
    response = await client.post(f"{api}/auth/register", json=CUENTA)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_already_registered"


async def test_el_correo_se_normaliza(client: AsyncClient, api: str) -> None:
    await client.post(f"{api}/auth/register", json={**CUENTA, "email": "Victor@Memories.App"})
    response = await client.post(
        f"{api}/auth/login", json={"email": "victor@memories.app", "password": CUENTA["password"]}
    )

    assert response.status_code == 200


async def test_iniciar_sesion_devuelve_los_dos_tokens(client: AsyncClient, api: str) -> None:
    await client.post(f"{api}/auth/register", json=CUENTA)
    response = await client.post(
        f"{api}/auth/login", json={"email": CUENTA["email"], "password": CUENTA["password"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == CUENTA["email"]


async def test_una_contrasena_incorrecta_no_dice_si_el_correo_existe(
    client: AsyncClient, api: str
) -> None:
    await client.post(f"{api}/auth/register", json=CUENTA)

    existente = await client.post(
        f"{api}/auth/login", json={"email": CUENTA["email"], "password": "otraClaveMala1"}
    )
    inexistente = await client.post(
        f"{api}/auth/login", json={"email": "nadie@memories.app", "password": "otraClaveMala1"}
    )

    assert existente.status_code == inexistente.status_code == 401
    assert existente.json()["error"]["message"] == inexistente.json()["error"]["message"]


async def test_el_perfil_requiere_token(client: AsyncClient, api: str) -> None:
    assert (await client.get(f"{api}/users/me")).status_code == 401


async def test_el_perfil_devuelve_al_usuario_autenticado(
    client: AsyncClient, api: str, auth_headers: dict[str, str]
) -> None:
    response = await client.get(f"{api}/users/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["email"] == CUENTA["email"]


async def test_renovar_la_sesion_invalida_el_refresh_token_usado(
    client: AsyncClient, api: str
) -> None:
    await client.post(f"{api}/auth/register", json=CUENTA)
    login = await client.post(
        f"{api}/auth/login", json={"email": CUENTA["email"], "password": CUENTA["password"]}
    )
    primer_refresh = login.json()["refresh_token"]

    renovacion = await client.post(f"{api}/auth/refresh", json={"refresh_token": primer_refresh})
    assert renovacion.status_code == 200
    assert renovacion.json()["refresh_token"] != primer_refresh

    reintento = await client.post(f"{api}/auth/refresh", json={"refresh_token": primer_refresh})
    assert reintento.status_code == 401


async def test_cerrar_sesion_invalida_el_refresh_token(client: AsyncClient, api: str) -> None:
    await client.post(f"{api}/auth/register", json=CUENTA)
    login = await client.post(
        f"{api}/auth/login", json={"email": CUENTA["email"], "password": CUENTA["password"]}
    )
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    cierre = await client.post(
        f"{api}/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers=headers
    )
    assert cierre.status_code == 200

    renovacion = await client.post(
        f"{api}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert renovacion.status_code == 401


async def test_listar_usuarios_es_solo_para_el_superusuario(
    client: AsyncClient,
    api: str,
    login_as: Callable[..., Awaitable[dict[str, str]]],
) -> None:
    headers = await login_as()
    response = await client.get(f"{api}/users", headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"
