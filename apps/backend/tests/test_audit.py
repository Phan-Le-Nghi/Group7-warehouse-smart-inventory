from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from os import getenv
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from warehouse_api.audit import create_audit
from warehouse_api.auth import WAREHOUSE_STAFF, Actor, Role, get_actor
from warehouse_api.db import get_db_session
from warehouse_api.main import app
from warehouse_api.models import (
    AuditLine,
    AuditSession,
    Base,
    InternalLocation,
    PickAllocation,
    PutawayAllocation,
    Receive,
    Sku,
    StockBalance,
    Transfer,
    User,
    Warehouse,
)
from warehouse_api.schemas import AuditRequest


@dataclass(frozen=True, slots=True)
class AuditFixture:
    warehouse_id: UUID
    first_sku_id: UUID
    second_sku_id: UUID
    backroom_id: UUID
    shelf_id: UUID
    foreign_location_id: UUID
    actor: Actor


@pytest.fixture
def audit_api() -> Iterator[tuple[TestClient, sessionmaker[Session], AuditFixture]]:
    database_url = getenv("TEST_DATABASE_URL")
    engine = (
        create_engine(database_url)
        if database_url
        else create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    )
    Base.metadata.create_all(engine)
    fixture = AuditFixture(
        warehouse_id=uuid4(),
        first_sku_id=uuid4(),
        second_sku_id=uuid4(),
        backroom_id=uuid4(),
        shelf_id=uuid4(),
        foreign_location_id=uuid4(),
        actor=Actor(uuid4(), "audit.staff", WAREHOUSE_STAFF),
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
        canonical = Warehouse(id=fixture.warehouse_id, code=f"W-{uuid4().hex}")
        session.add_all(
            [
                User(
                    id=fixture.actor.user_id,
                    login_identifier=fixture.actor.login_identifier,
                    password_hash="test-only",
                    role=fixture.actor.role.value,
                ),
                canonical,
                Sku(id=fixture.first_sku_id, code=f"SKU-A-{uuid4().hex}"),
                Sku(id=fixture.second_sku_id, code=f"SKU-B-{uuid4().hex}"),
            ]
        )
        session.flush()
        session.add_all(
            [
                InternalLocation(
                    id=fixture.backroom_id,
                    warehouse_id=canonical.id,
                    code="BACKROOM",
                ),
                InternalLocation(
                    id=fixture.shelf_id,
                    warehouse_id=canonical.id,
                    code="SALES_SHELF",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                StockBalance(
                    sku_id=fixture.first_sku_id,
                    location_id=fixture.backroom_id,
                    quantity=12,
                ),
                StockBalance(
                    sku_id=fixture.first_sku_id,
                    location_id=fixture.shelf_id,
                    quantity=6,
                ),
                StockBalance(
                    sku_id=fixture.second_sku_id,
                    location_id=fixture.backroom_id,
                    quantity=4,
                ),
            ]
        )

    def override_session() -> Iterator[Session]:
        with factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_actor] = lambda: fixture.actor
    with TestClient(app) as client:
        yield client, factory, fixture
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def line(sku_id: UUID, location_id: UUID, physical: object) -> dict[str, object]:
    return {
        "sku_id": str(sku_id),
        "location_id": str(location_id),
        "physical_quantity": physical,
    }


def request(
    fixture: AuditFixture,
    *,
    lines: list[dict[str, object]] | None = None,
    scope_type: str = "SELECTED_PAIRS",
) -> dict[str, object]:
    return {
        "scope_type": scope_type,
        "lines": lines
        if lines is not None
        else [line(fixture.first_sku_id, fixture.backroom_id, 12)],
    }


def stock_snapshot(factory: sessionmaker[Session]) -> list[tuple[UUID, UUID, int]]:
    with factory() as session:
        return list(
            session.execute(
                select(
                    StockBalance.sku_id,
                    StockBalance.location_id,
                    StockBalance.quantity,
                ).order_by(StockBalance.sku_id, StockBalance.location_id)
            ).all()
        )


def test_context_returns_full_matrix_and_missing_balance_zero(audit_api) -> None:
    client, factory, fixture = audit_api
    before = stock_snapshot(factory)
    response = client.get("/api/v1/audits/context")
    assert response.status_code == 200
    body = response.json()
    assert body["warehouse_id"] == str(fixture.warehouse_id)
    assert len(body["pairs"]) == 4
    quantities = {
        (item["sku_id"], item["location_id"]): item["preview_system_quantity"]
        for item in body["pairs"]
    }
    assert quantities[(str(fixture.second_sku_id), str(fixture.shelf_id))] == 0
    assert stock_snapshot(factory) == before


def test_selected_multiline_records_discrepancies_without_stock_effect(
    audit_api,
) -> None:
    client, factory, fixture = audit_api
    before = stock_snapshot(factory)
    response = client.post(
        "/api/v1/audits",
        json=request(
            fixture,
            lines=[
                line(fixture.second_sku_id, fixture.shelf_id, 3),
                line(fixture.first_sku_id, fixture.backroom_id, 12),
            ],
        ),
        headers={"Idempotency-Key": "selected-multi"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["result"] == "MISMATCH"
    assert body["status"] == "MISMATCH_RECORDED"
    line_results = {
        (item["sku_id"], item["location_id"]): (
            item["system_quantity"],
            item["quantity_discrepancy"],
            item["result"],
        )
        for item in body["lines"]
    }
    assert line_results[(str(fixture.first_sku_id), str(fixture.backroom_id))] == (
        12,
        0,
        "MATCH",
    )
    assert line_results[(str(fixture.second_sku_id), str(fixture.shelf_id))] == (
        0,
        3,
        "MISMATCH",
    )
    assert stock_snapshot(factory) == before
    with factory() as session:
        assert session.scalar(select(func.count(StockBalance.id))) == 3
        assert session.scalar(select(func.count(Receive.id))) == 0
        assert session.scalar(select(func.count(PutawayAllocation.id))) == 0
        assert session.scalar(select(func.count(PickAllocation.id))) == 0
        assert session.scalar(select(func.count(Transfer.id))) == 0


def test_whole_warehouse_match_uses_exact_matrix(audit_api) -> None:
    client, _factory, fixture = audit_api
    context = client.get("/api/v1/audits/context").json()
    lines = [
        {
            "sku_id": pair["sku_id"],
            "location_id": pair["location_id"],
            "physical_quantity": pair["preview_system_quantity"],
        }
        for pair in reversed(context["pairs"])
    ]
    response = client.post(
        "/api/v1/audits",
        json=request(fixture, lines=lines, scope_type="WHOLE_WAREHOUSE"),
        headers={"Idempotency-Key": "whole-match"},
    )
    assert response.status_code == 201
    assert response.json()["result"] == "MATCH"
    assert response.json()["status"] == "MATCH_COMPLETED"
    assert len(response.json()["lines"]) == 4


def test_negative_discrepancy_is_recorded(audit_api) -> None:
    client, _factory, fixture = audit_api
    response = client.post(
        "/api/v1/audits",
        json=request(
            fixture,
            lines=[line(fixture.first_sku_id, fixture.backroom_id, 10)],
        ),
        headers={"Idempotency-Key": "negative-discrepancy"},
    )
    assert response.status_code == 201
    assert response.json()["lines"][0]["quantity_discrepancy"] == -2
    assert response.json()["lines"][0]["result"] == "MISMATCH"


def test_whole_warehouse_scope_change_has_no_write(audit_api) -> None:
    client, factory, fixture = audit_api
    context = client.get("/api/v1/audits/context").json()
    lines = [
        {
            "sku_id": pair["sku_id"],
            "location_id": pair["location_id"],
            "physical_quantity": pair["preview_system_quantity"],
        }
        for pair in context["pairs"]
    ]
    with factory.begin() as session:
        session.add(Sku(code=f"ADDED-{uuid4().hex}"))
    response = client.post(
        "/api/v1/audits",
        json=request(fixture, lines=lines, scope_type="WHOLE_WAREHOUSE"),
        headers={"Idempotency-Key": "scope-changed"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "AUDIT_SCOPE_CHANGED"
    with factory() as session:
        assert session.scalar(select(func.count(AuditSession.id))) == 0


def test_replay_returns_original_historical_snapshot_before_scope_checks(
    audit_api,
) -> None:
    client, factory, fixture = audit_api
    context = client.get("/api/v1/audits/context").json()
    payload = request(
        fixture,
        scope_type="WHOLE_WAREHOUSE",
        lines=[
            {
                "sku_id": pair["sku_id"],
                "location_id": pair["location_id"],
                "physical_quantity": pair["preview_system_quantity"],
            }
            for pair in context["pairs"]
        ],
    )
    headers = {"Idempotency-Key": "historical-replay"}
    first = client.post("/api/v1/audits", json=payload, headers=headers)
    assert first.status_code == 201
    with factory.begin() as session:
        balance = session.scalar(
            select(StockBalance).where(
                StockBalance.sku_id == fixture.first_sku_id,
                StockBalance.location_id == fixture.backroom_id,
            )
        )
        assert balance is not None
        balance.quantity = 2
        session.add(Sku(code=f"SCOPE-CHANGE-{uuid4().hex}"))
    replay = client.post("/api/v1/audits", json=payload, headers=headers)
    assert replay.status_code == 200
    assert replay.json() == first.json()
    with factory() as session:
        assert session.scalar(select(func.count(AuditSession.id))) == 1


def test_same_key_different_command_conflicts(audit_api) -> None:
    client, _factory, fixture = audit_api
    headers = {"Idempotency-Key": "reused"}
    assert (
        client.post(
            "/api/v1/audits", json=request(fixture), headers=headers
        ).status_code
        == 201
    )
    conflict = client.post(
        "/api/v1/audits",
        json=request(
            fixture,
            lines=[line(fixture.first_sku_id, fixture.backroom_id, 11)],
        ),
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


@pytest.mark.parametrize("quantity", [-1, 1.5, "1", True, 2_147_483_648])
def test_invalid_quantity_is_typed(audit_api, quantity: object) -> None:
    client, _factory, fixture = audit_api
    response = client.post(
        "/api/v1/audits",
        json=request(
            fixture,
            lines=[line(fixture.first_sku_id, fixture.backroom_id, quantity)],
        ),
        headers={"Idempotency-Key": f"invalid-{quantity}"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_QUANTITY"


def test_empty_duplicate_and_invalid_key_are_typed(audit_api) -> None:
    client, _factory, fixture = audit_api
    empty = client.post(
        "/api/v1/audits",
        json=request(fixture, lines=[]),
        headers={"Idempotency-Key": "empty"},
    )
    duplicate_line = line(fixture.first_sku_id, fixture.backroom_id, 12)
    duplicate = client.post(
        "/api/v1/audits",
        json=request(fixture, lines=[duplicate_line, duplicate_line]),
        headers={"Idempotency-Key": "duplicate"},
    )
    missing_key = client.post("/api/v1/audits", json=request(fixture))
    whitespace_key = client.post(
        "/api/v1/audits",
        json=request(fixture),
        headers={"Idempotency-Key": "   "},
    )
    assert empty.json()["error"]["code"] == "EMPTY_AUDIT_SCOPE"
    assert duplicate.json()["error"]["code"] == "DUPLICATE_AUDIT_LINE"
    assert missing_key.json()["error"]["code"] == "INVALID_IDEMPOTENCY_KEY"
    assert whitespace_key.json()["error"]["code"] == "INVALID_IDEMPOTENCY_KEY"


def test_unknown_references_are_typed(audit_api) -> None:
    client, _factory, fixture = audit_api
    cases = [
        (
            line(uuid4(), fixture.backroom_id, 0),
            "unknown-sku",
            404,
            "SKU_NOT_FOUND",
        ),
        (
            line(fixture.first_sku_id, uuid4(), 0),
            "unknown-location",
            404,
            "LOCATION_NOT_FOUND",
        ),
    ]
    for audit_line, key, status, code in cases:
        response = client.post(
            "/api/v1/audits",
            json=request(fixture, lines=[audit_line]),
            headers={"Idempotency-Key": key},
        )
        assert response.status_code == status
        assert response.json()["error"]["code"] == code


def test_foreign_warehouse_location_is_typed(
    audit_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, factory, fixture = audit_api
    with factory.begin() as session:
        foreign = Warehouse(code=f"FOREIGN-{uuid4().hex}")
        session.add(foreign)
        session.flush()
        session.add(
            InternalLocation(
                id=fixture.foreign_location_id,
                warehouse_id=foreign.id,
                code="BACKROOM",
            )
        )
    monkeypatch.setattr(
        "warehouse_api.audit._canonical_warehouse_id",
        lambda _session: fixture.warehouse_id,
    )
    response = client.post(
        "/api/v1/audits",
        json=request(
            fixture,
            lines=[line(fixture.first_sku_id, fixture.foreign_location_id, 0)],
        ),
        headers={"Idempotency-Key": "foreign-location"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "LOCATION_OUTSIDE_WAREHOUSE"


@pytest.mark.parametrize("role", [Role.MANAGER, Role.PURCHASING, Role.ADMIN])
def test_wrong_roles_are_forbidden(audit_api, role: Role) -> None:
    client, factory, fixture = audit_api
    app.dependency_overrides[get_actor] = lambda: Actor(uuid4(), "wrong.role", role)
    assert client.get("/api/v1/audits/context").status_code == 403
    response = client.post(
        "/api/v1/audits",
        json=request(fixture),
        headers={"Idempotency-Key": f"forbidden-{role}"},
    )
    assert response.status_code == 403
    with factory() as session:
        assert session.scalar(select(func.count(AuditSession.id))) == 0


def test_unauthenticated_is_rejected(audit_api) -> None:
    client, _factory, _fixture = audit_api
    del app.dependency_overrides[get_actor]
    assert client.get("/api/v1/audits/context").status_code == 401


def test_persistence_failure_rolls_back_session_and_lines(
    audit_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    _client, factory, fixture = audit_api
    command = AuditRequest.model_validate(request(fixture))
    with factory() as session:
        monkeypatch.setattr(
            session,
            "flush",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("simulated persistence failure")
            ),
        )
        with pytest.raises(RuntimeError, match="simulated persistence failure"):
            create_audit(session, command, fixture.actor, "rollback")
        session.rollback()
    with factory() as session:
        assert session.scalar(select(func.count(AuditSession.id))) == 0
        assert session.scalar(select(func.count(AuditLine.id))) == 0


def test_database_constraints_reject_inconsistent_rows(audit_api) -> None:
    _client, factory, fixture = audit_api
    audit_id = uuid4()
    with factory.begin() as session:
        session.add(
            AuditSession(
                id=audit_id,
                warehouse_id=fixture.warehouse_id,
                scope_type="SELECTED_PAIRS",
                result="MATCH",
                status="MATCH_COMPLETED",
                audited_by_user_id=fixture.actor.user_id,
                audited_at=datetime.now(UTC),
                idempotency_key="constraint-parent",
                request_fingerprint="a" * 64,
            )
        )
    with pytest.raises(IntegrityError), factory.begin() as session:
        session.add(
            AuditLine(
                audit_id=audit_id,
                sku_id=fixture.first_sku_id,
                location_id=fixture.backroom_id,
                system_quantity=12,
                physical_quantity=10,
                quantity_discrepancy=-1,
                result="MATCH",
            )
        )
        session.flush()
    with pytest.raises(IntegrityError), factory.begin() as session:
        session.add(
            AuditSession(
                warehouse_id=fixture.warehouse_id,
                scope_type="WHOLE_WAREHOUSE",
                result="MATCH",
                status="MISMATCH_RECORDED",
                audited_by_user_id=fixture.actor.user_id,
                audited_at=datetime.now(UTC),
                idempotency_key="bad-result-status",
                request_fingerprint="b" * 64,
            )
        )
        session.flush()
