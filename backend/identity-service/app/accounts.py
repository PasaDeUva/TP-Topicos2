from sqlalchemy.orm import Session

from app.models import Account
from app.passwords import hash_password


def create_account(session: Session, email: str, password: str) -> Account:
    account = Account(email=email, password_hash=hash_password(password))
    session.add(account)
    session.flush()
    return account
