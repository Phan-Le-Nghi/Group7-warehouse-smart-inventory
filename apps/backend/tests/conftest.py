from collections.abc import Callable, Iterator
from os import getenv

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from warehouse_api.auth_service import hash_password, normalize_login_identifier
from warehouse_api.db import get_db_session
from warehouse_api.main import app
from warehouse_api.models import Base, User


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    test_database_url = getenv("TEST_DATABASE_URL")
    if test_database_url:
        engine = create_engine(test_database_url)
    else:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session
        session.rollback()


@pytest.fixture
def user_factory(
    db_session: Session,
) -> Callable[..., User]:
    def create_user(
        login_identifier: str = "demo.warehouse_staff",
        password: str = "test-only-password",
        role: str = "WAREHOUSE_STAFF",
        is_active: bool = True,
    ) -> User:
        user = User(
            login_identifier=normalize_login_identifier(login_identifier),
            password_hash=hash_password(password),
            role=role,
            is_active=is_active,
        )
        db_session.add(user)
        db_session.flush()
        return user

    return create_user


@pytest.fixture
def api_client(
    session_factory: sessionmaker[Session],
) -> Iterator[TestClient]:
    def override_session() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
