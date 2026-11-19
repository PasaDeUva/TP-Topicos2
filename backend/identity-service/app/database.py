import os
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@lru_cache
def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def get_session() -> Iterator[Session]:
    with Session(_engine()) as session:
        yield session
