import os

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher


def _password_hasher() -> PasswordHash:
    return PasswordHash(
        (
            Argon2Hasher(
                time_cost=int(os.getenv("PASSWORD_HASH_TIME_COST", "3")),
                memory_cost=int(os.getenv("PASSWORD_HASH_MEMORY_COST", "65536")),
                parallelism=int(os.getenv("PASSWORD_HASH_PARALLELISM", "4")),
            ),
        )
    )


def hash_password(password: str) -> str:
    return _password_hasher().hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hasher().verify(password, password_hash)
