"""Cifrado simétrico (Fernet) de secretos guardados en la BD, como la clave personal de Garmin.

La clave se toma de `APP_ENCRYPTION_KEY` (clave Fernet). Si no está definida se deriva de
`APP_JWT_SECRET`, así que en producción cualquiera de las dos debe ser secreta.
"""

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class DecryptionError(Exception):
    """El secreto no se puede descifrar (clave de cifrado cambiada o dato corrupto)."""


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    if settings.encryption_key:
        return Fernet(settings.encryption_key.encode())
    digest = hashlib.sha256(f"traingapp-secrets:{settings.jwt_secret}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise DecryptionError("No se pudo descifrar el secreto guardado") from exc
