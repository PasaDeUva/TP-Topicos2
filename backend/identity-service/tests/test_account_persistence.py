import os
import uuid

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts import create_account
from app.models import Account
from app.passwords import verify_password


@pytest.fixture
def session():
    url = os.environ.get("IDENTITY_TEST_DATABASE_URL")
    if not url:
        pytest.fail("IDENTITY_TEST_DATABASE_URL is required for PostgreSQL persistence tests")
    engine = create_engine(url)
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            yield db
        transaction.rollback()
    engine.dispose()


def test_password_is_hashed_before_persistence(session):
    password = "a valid password"
    account = create_account(session, f"{uuid.uuid4()}@example.com", password)
    session.expire_all()

    stored = session.scalar(select(Account).where(Account.id == account.id))
    assert stored.password_hash != password
    assert stored.password_hash.startswith("$argon2id$")
    assert verify_password(password, stored.password_hash)
    assert not verify_password("incorrect password", stored.password_hash)


def test_duplicate_email_is_rejected_by_database(session):
    email = f"{uuid.uuid4()}@example.com"
    create_account(session, email, "a valid password")

    with pytest.raises(IntegrityError) as error:
        create_account(session, email, "another password")
    assert error.value.orig.diag.constraint_name == "uq_accounts_email"


def test_migrated_email_constraint_has_explicit_name(session):
    name = session.scalar(text("SELECT conname FROM pg_constraint WHERE conrelid = 'accounts'::regclass AND contype = 'u'"))
    assert name == "uq_accounts_email"
