"""Entidad PrivacyConsent: qué versión de la política aceptó cada usuario (RN-50)."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.shared.entities.errors import BusinessRuleError
from app.shared.entities.ids import new_id


class PrivacyPolicyNotAcceptedError(BusinessRuleError):
    code = "privacy_policy_not_accepted"
    message = "Debes aceptar la política de privacidad para registrarte."


def ensure_policy_accepted(accepted: bool) -> None:
    if not accepted:
        raise PrivacyPolicyNotAcceptedError


@dataclass(frozen=True)
class PrivacyConsent:
    id: uuid.UUID
    user_id: uuid.UUID
    policy_version: str
    accepted_at: datetime

    @classmethod
    def accept(
        cls, *, user_id: uuid.UUID, policy_version: str, now: datetime
    ) -> "PrivacyConsent":
        return cls(
            id=new_id(), user_id=user_id, policy_version=policy_version, accepted_at=now
        )
