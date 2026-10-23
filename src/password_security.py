"""Password hashing and verification for production authentication."""

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password minimal 12 karakter")

    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False