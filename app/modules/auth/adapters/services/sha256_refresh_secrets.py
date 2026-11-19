"""RefreshSecrets: secreto aleatorio de 256 bits guardado como SHA-256 (D56).

El secreto es aleatorio y largo, así que no necesita un hash lento como
Argon2 (specs/auth/design.md §3).
"""

import hashlib
import hmac
import secrets


class Sha256RefreshSecrets:
    def new_secret(self) -> str:
        return secrets.token_urlsafe(32)

    def hash(self, secret: str) -> str:
        return hashlib.sha256(secret.encode()).hexdigest()

    def matches(self, secret: str, stored_hash: str) -> bool:
        # compare_digest: el tiempo de comparación no revela el hash.
        return hmac.compare_digest(self.hash(secret), stored_hash)
