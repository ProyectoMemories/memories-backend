"""Traducción entre modelos ORM y entidades, en los dos sentidos."""

from app.modules.auth.adapters.gateways.orm_models import (
    PrivacyConsentRecord,
    UserRecord,
    UserSessionRecord,
)
from app.modules.auth.entities.privacy_consent import PrivacyConsent
from app.modules.auth.entities.user import User
from app.modules.auth.entities.user_session import UserSession


def user_to_entity(record: UserRecord) -> User:
    return User(
        id=record.id,
        username=record.username,
        email=record.email,
        password_hash=record.password_hash,
        first_name=record.first_name,
        paternal_surname=record.paternal_surname,
        maternal_surname=record.maternal_surname,
        birth_date=record.birth_date,
        status=record.status,
        email_verified_at=record.email_verified_at,
        deletion_requested_at=record.deletion_requested_at,
    )


def new_user_record(user: User) -> UserRecord:
    return UserRecord(
        id=user.id,
        username=user.username,
        email=user.email,
        password_hash=user.password_hash,
        first_name=user.first_name,
        paternal_surname=user.paternal_surname,
        maternal_surname=user.maternal_surname,
        birth_date=user.birth_date,
        status=user.status,
        email_verified_at=user.email_verified_at,
        deletion_requested_at=user.deletion_requested_at,
    )


def copy_user_changes(user: User, record: UserRecord) -> None:
    """Solo los campos que el negocio puede cambiar."""
    record.password_hash = user.password_hash
    record.status = user.status
    record.email_verified_at = user.email_verified_at
    record.deletion_requested_at = user.deletion_requested_at


def new_consent_record(consent: PrivacyConsent) -> PrivacyConsentRecord:
    return PrivacyConsentRecord(
        id=consent.id,
        user_id=consent.user_id,
        policy_version=consent.policy_version,
        accepted_at=consent.accepted_at,
    )


def session_to_entity(record: UserSessionRecord) -> UserSession:
    return UserSession(
        id=record.id,
        user_id=record.user_id,
        refresh_token_hash=record.refresh_token_hash,
        platform=record.platform,
        device_name=record.device_name,
        created_at=record.created_at,
        last_used_at=record.last_used_at,
        expires_at=record.expires_at,
        revoked_at=record.revoked_at,
    )


def new_session_record(user_session: UserSession) -> UserSessionRecord:
    return UserSessionRecord(
        id=user_session.id,
        user_id=user_session.user_id,
        refresh_token_hash=user_session.refresh_token_hash,
        platform=user_session.platform,
        device_name=user_session.device_name,
        created_at=user_session.created_at,
        last_used_at=user_session.last_used_at,
        expires_at=user_session.expires_at,
        revoked_at=user_session.revoked_at,
    )


def copy_session_changes(user_session: UserSession, record: UserSessionRecord) -> None:
    record.refresh_token_hash = user_session.refresh_token_hash
    record.last_used_at = user_session.last_used_at
    record.expires_at = user_session.expires_at
    record.revoked_at = user_session.revoked_at
