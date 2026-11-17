import argparse
import getpass
import os

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.accounts import create_account
from app.database import _engine
from app.models import Account, RoleAssignment, Session as LoginSession
from app.passwords import hash_password


def initialize_admin(session: Session, email: str, password: str) -> bool:
    email = TypeAdapter(EmailStr).validate_python(email)
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")
    session.execute(text("SELECT pg_advisory_xact_lock(72486101)"))
    existing = session.scalar(select(RoleAssignment.id).where(RoleAssignment.role == "administrador"))
    if existing is not None:
        return False
    if session.scalar(select(Account.id).where(Account.email == email)) is not None:
        raise ValueError("Administrator email already belongs to an account")
    account = create_account(session, email, password)
    session.add(RoleAssignment(account_id=account.id, role="administrador", status="activo"))
    session.flush()
    return True


def recover_admin(session: Session, email: str, password: str) -> None:
    email = TypeAdapter(EmailStr).validate_python(email)
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")
    account = session.scalar(
        select(Account).join(RoleAssignment, RoleAssignment.account_id == Account.id)
        .where(Account.email == email, RoleAssignment.role == "administrador")
        .with_for_update(of=Account)
    )
    if account is None:
        raise ValueError("Administrator not found")
    account.password_hash = hash_password(password)
    session.execute(
        update(LoginSession)
        .where(LoginSession.account_id == account.id, LoginSession.revoked.is_(False))
        .values(revoked=True)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the initial administrator")
    parser.add_argument("action", choices=("initialize", "recover"))
    args = parser.parse_args()
    email = os.environ["ADMIN_EMAIL"]
    password = os.environ["ADMIN_PASSWORD"] if args.action == "initialize" else getpass.getpass("New password: ")
    with Session(_engine()) as session:
        if args.action == "initialize":
            initialize_admin(session, email, password)
        else:
            recover_admin(session, email, password)
        session.commit()


if __name__ == "__main__":
    main()
