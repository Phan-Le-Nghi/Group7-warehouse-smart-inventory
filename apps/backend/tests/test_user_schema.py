import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from warehouse_api.auth_service import hash_password
from warehouse_api.models import User


def _user(login_identifier: str) -> User:
    return User(
        login_identifier=login_identifier,
        password_hash=hash_password("test-only-password"),
        role="MANAGER",
        is_active=True,
    )


@pytest.mark.parametrize(
    "login_identifier", ("Demo.Manager", " demo.manager ", "DEMO.MANAGER")
)
def test_database_rejects_noncanonical_login_identifier(
    db_session: Session, login_identifier: str
) -> None:
    db_session.add(_user(login_identifier))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_database_accepts_normalized_login_identifier(db_session: Session) -> None:
    user = _user("demo.manager")
    db_session.add(user)
    db_session.flush()

    assert user.login_identifier == "demo.manager"


def test_semantic_duplicate_cannot_be_persisted(db_session: Session) -> None:
    db_session.add(_user("demo.manager"))
    db_session.flush()
    db_session.add(_user("Demo.Manager"))

    with pytest.raises(IntegrityError):
        db_session.flush()
