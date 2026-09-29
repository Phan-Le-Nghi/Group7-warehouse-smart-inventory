import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from warehouse_api.auth_service import verify_password
from warehouse_api.demo_seed import DEMO_USERS, main, seed_demo_users
from warehouse_api.models import User


def test_demo_seed_is_idempotent_and_uses_all_approved_roles(
    db_session: Session,
) -> None:
    password = "test-only-demo-password"

    first = seed_demo_users(db_session, password)
    hashes_after_first = {
        user.login_identifier: user.password_hash
        for user in db_session.scalars(select(User)).all()
    }
    second = seed_demo_users(db_session, password)

    assert first.created == 4
    assert second.unchanged == 4
    assert db_session.scalar(select(func.count(User.id))) == 4
    users = db_session.scalars(select(User)).all()
    assert {(user.login_identifier, user.role) for user in users} == {
        (identifier, role.value) for identifier, role in DEMO_USERS
    }
    assert all(verify_password(password, user.password_hash) for user in users)
    assert {
        user.login_identifier: user.password_hash for user in users
    } == hashes_after_first


def test_demo_seed_does_not_print_password(db_session: Session, capsys) -> None:
    password = "secret-that-must-not-be-printed"

    seed_demo_users(db_session, password)

    captured = capsys.readouterr()
    assert password not in captured.out
    assert password not in captured.err


def test_demo_seed_is_disabled_in_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEMO_USER_PASSWORD", "must-not-be-used")

    with pytest.raises(RuntimeError, match="disabled"):
        main()
