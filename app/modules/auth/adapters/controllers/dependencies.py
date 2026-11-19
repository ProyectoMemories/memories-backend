"""Inyección de dependencias de los controllers de auth.

Los controllers piden los interactores a una fábrica que `frameworks/` deja en
`request.state.auth` al inicio de cada petición. Así este círculo no importa
`frameworks/` (regla de dependencias, CLAUDE.md §7).
"""

from typing import Annotated, Protocol

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.modules.auth.use_cases.authenticate import Authenticate, AuthenticatedUser
from app.modules.auth.use_cases.errors import NotAuthenticatedError
from app.modules.auth.use_cases.log_in import LogIn
from app.modules.auth.use_cases.log_out import LogOut
from app.modules.auth.use_cases.refresh_session import RefreshSession
from app.modules.auth.use_cases.register_user import RegisterUser
from app.modules.auth.use_cases.resend_verification import ResendVerification
from app.modules.auth.use_cases.verify_email import VerifyEmail


class AuthUseCases(Protocol):
    """Lo que los controllers necesitan; lo implementa frameworks/composition.py."""

    def register_user(self) -> RegisterUser: ...
    def verify_email(self) -> VerifyEmail: ...
    def resend_verification(self) -> ResendVerification: ...
    def log_in(self) -> LogIn: ...
    def refresh_session(self) -> RefreshSession: ...
    def log_out(self) -> LogOut: ...
    def authenticate(self) -> Authenticate: ...


def get_auth_use_cases(request: Request) -> AuthUseCases:
    use_cases: AuthUseCases = request.state.auth  # lo deja main.open_request_scope
    return use_cases


UseCases = Annotated[AuthUseCases, Depends(get_auth_use_cases)]

# auto_error=False: sin cabecera responde nuestro 401 con {code, message}.
_bearer = HTTPBearer(auto_error=False, description="Token de acceso (15 min)")


def get_current_user(
    use_cases: UseCases,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthenticatedUser:
    """Usuario de la petición. Los demás módulos dependen de esto (CLAUDE.md §7)."""
    if credentials is None:
        raise NotAuthenticatedError
    return use_cases.authenticate().execute(credentials.credentials)


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
