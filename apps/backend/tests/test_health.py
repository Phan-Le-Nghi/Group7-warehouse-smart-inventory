from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from warehouse_api import main

client = TestClient(main.app)


def test_health_is_db_independent(monkeypatch) -> None:
    def unavailable_database() -> None:
        raise SQLAlchemyError("sensitive database detail")

    monkeypatch.setattr(main, "check_database_ready", unavailable_database)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_succeeds_when_database_is_reachable(monkeypatch) -> None:
    monkeypatch.setattr(main, "check_database_ready", lambda: None)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_returns_generic_failure_without_leaking_details(monkeypatch) -> None:
    sensitive_detail = "postgresql://user:password@db.example.com/warehouse"

    def unavailable_database() -> None:
        raise SQLAlchemyError(sensitive_detail)

    monkeypatch.setattr(main, "check_database_ready", unavailable_database)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert sensitive_detail not in response.text
