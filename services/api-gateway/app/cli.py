"""Utilidades de administración desde el PC (no expuestas por la API).

Uso (desde services/api-gateway):
    .venv\\Scripts\\python -m app.cli reset-password tu@email.com
    .venv\\Scripts\\python -m app.cli logout-all tu@email.com
    .venv\\Scripts\\python -m app.cli init-secrets   # una vez: secretos fuertes en los .env
"""

import argparse
import asyncio
import getpass
import secrets
import sys
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select

from app.core import crypto
from app.core.database import async_session_factory
from app.crud import users
from app.models import GarminConnection
from app.services import auth_sessions

MIN_PASSWORD = 8
GATEWAY_ENV = Path(__file__).resolve().parents[1] / ".env"
PARSER_ENV = Path(__file__).resolve().parents[2] / "ai-parser" / ".env"


def _read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    pairs = (line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines())
    return {k.strip(): v.strip() for k, *rest in pairs if not k.startswith("#") for v in rest}


def _set_env(path: Path, values: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    pending = dict(values)
    for i, line in enumerate(lines):
        key = line.split("=", 1)[0].strip()
        if key in pending:
            lines[i] = f"{key}={pending.pop(key)}"
    lines += [f"{key}={value}" for key, value in pending.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _recrypt(value: str | None, old: Fernet, new: Fernet) -> str | None:
    if value is None:
        return None
    try:
        return new.encrypt(old.decrypt(value.encode())).decode()
    except InvalidToken:
        return value  # ya cifrado con la clave nueva o ilegible: se deja igual


async def _init_secrets() -> int:
    current = _read_env(GATEWAY_ENV)
    if current.get("APP_JWT_SECRET") and current.get("APP_ENCRYPTION_KEY"):
        print("Los secretos ya están configurados en services/api-gateway/.env.")
        return 0
    old = crypto._fernet()
    new_key = Fernet.generate_key()
    new = Fernet(new_key)
    async with async_session_factory() as session:
        conns = list(await session.scalars(select(GarminConnection)))
        for conn in conns:
            conn.api_key_enc = _recrypt(conn.api_key_enc, old, new) or conn.api_key_enc
            conn.token_enc = _recrypt(conn.token_enc, old, new)
        await session.commit()
    internal = secrets.token_urlsafe(48)
    _set_env(
        GATEWAY_ENV,
        {
            "APP_JWT_SECRET": secrets.token_urlsafe(64),
            "APP_INTERNAL_TOKEN": internal,
            "APP_ENCRYPTION_KEY": new_key.decode(),
        },
    )
    _set_env(PARSER_ENV, {"APP_INTERNAL_TOKEN": internal})
    print("Secretos generados (no se muestran):")
    print("  services/api-gateway/.env: APP_JWT_SECRET, APP_INTERNAL_TOKEN, APP_ENCRYPTION_KEY")
    print("  services/ai-parser/.env:   APP_INTERNAL_TOKEN")
    print(f"  Claves de Garmin re-cifradas: {len(conns)}")
    print("Reinicia los servicios. Todas las sesiones se cierran: vuelve a iniciar sesión.")
    return 0


async def _reset_password(email: str, password: str) -> int:
    async with async_session_factory() as session:
        user = await users.get_by_email(session, email)
        if user is None:
            print(f"No existe ningún usuario con el email {email}", file=sys.stderr)
            return 1
        await users.update_password(session, user, password)
        await auth_sessions.revoke_all(session, user)
    print("Contraseña cambiada y sesiones cerradas en todos los dispositivos.")
    return 0


async def _logout_all(email: str) -> int:
    async with async_session_factory() as session:
        user = await users.get_by_email(session, email)
        if user is None:
            print(f"No existe ningún usuario con el email {email}", file=sys.stderr)
            return 1
        await auth_sessions.revoke_all(session, user)
    print("Sesiones cerradas en todos los dispositivos.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    reset = sub.add_parser("reset-password", help="Cambia la contraseña de un usuario")
    reset.add_argument("email")
    logout = sub.add_parser("logout-all", help="Cierra todas las sesiones de un usuario")
    logout.add_argument("email")
    sub.add_parser("init-secrets", help="Genera secretos fuertes en los .env (una vez)")
    args = parser.parse_args(argv)

    if args.command == "init-secrets":
        return asyncio.run(_init_secrets())

    if args.command == "logout-all":
        return asyncio.run(_logout_all(args.email))
    password = getpass.getpass("Nueva contraseña: ")
    if len(password) < MIN_PASSWORD:
        print(f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres.", file=sys.stderr)
        return 1
    if getpass.getpass("Repítela: ") != password:
        print("Las contraseñas no coinciden.", file=sys.stderr)
        return 1
    return asyncio.run(_reset_password(args.email, password))


if __name__ == "__main__":
    raise SystemExit(main())
