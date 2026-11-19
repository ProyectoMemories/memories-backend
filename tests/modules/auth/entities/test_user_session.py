import uuid
from datetime import UTC, datetime, timedelta

from app.modules.auth.entities.user_session import ClientPlatform, UserSession

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
USER_ID = uuid.UUID("01900000-0000-7000-8000-000000000001")


def _session() -> UserSession:
    return UserSession.open(
        user_id=USER_ID,
        platform=ClientPlatform.ANDROID,
        device_name="Pixel 8",
        refresh_token_hash="hash-1",
        now=NOW,
    )


def test_una_sesion_nueva_dura_30_dias() -> None:
    user_session = _session()

    assert user_session.expires_at - user_session.created_at == timedelta(days=30)
    assert user_session.is_open(NOW + timedelta(days=29))
    assert not user_session.is_open(NOW + timedelta(days=30))


def test_solo_acepta_el_canal_en_que_se_abrio() -> None:
    user_session = _session()

    assert user_session.accepts(ClientPlatform.ANDROID, NOW)
    assert not user_session.accepts(ClientPlatform.WEB, NOW)


def test_rotar_cambia_el_hash_y_alarga_la_vida() -> None:
    user_session = _session()
    later = NOW + timedelta(days=10)

    user_session.rotate("hash-2", later)

    assert user_session.refresh_token_hash == "hash-2"
    assert user_session.last_used_at == later
    assert user_session.expires_at == later + timedelta(days=30)


def test_una_sesion_revocada_queda_cerrada() -> None:
    user_session = _session()

    user_session.revoke(NOW)

    assert not user_session.is_open(NOW)
    assert not user_session.accepts(ClientPlatform.ANDROID, NOW)


def test_sabe_de_quien_es() -> None:
    assert _session().belongs_to(USER_ID)
    assert not _session().belongs_to(uuid.uuid4())
