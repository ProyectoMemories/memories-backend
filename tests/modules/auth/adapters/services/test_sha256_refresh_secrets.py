from app.modules.auth.adapters.services.sha256_refresh_secrets import (
    Sha256RefreshSecrets,
)

secrets = Sha256RefreshSecrets()


def test_el_secreto_coincide_solo_con_su_hash() -> None:
    secret = secrets.new_secret()
    stored = secrets.hash(secret)

    assert secrets.matches(secret, stored)
    assert not secrets.matches(secrets.new_secret(), stored)
    assert secret not in stored


def test_cada_secreto_es_distinto_y_largo() -> None:
    first, second = secrets.new_secret(), secrets.new_secret()

    assert first != second
    assert len(first) >= 43  # 32 bytes en base64
