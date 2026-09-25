from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from os import getenv
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from warehouse_api.auth import Actor, Role, get_actor
from warehouse_api.db import get_db_session
from warehouse_api.main import app
from warehouse_api.models import (
    AuditLine,
    AuditRecheck,
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


@dataclass(frozen=True, slots=True)
class RecheckFixture:
    warehouse_id: UUID
    manager: Actor
    auditor_id: UUID
    backroom_id: UUID
    shelf_id: UUID
    first_sku_id: UUID
    second_sku_id: UUID
    newest_line_id: UUID
    older_line_id: UUID
    match_line_id: UUID


@pytest.fixture
def recheck_api() -> Iterator[tuple[TestClient, sessionmaker[Session], RecheckFixture]]:
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
    fixture = RecheckFixture(
        warehouse_id=uuid4(),
        manager=Actor(uuid4(), "audit.manager", Role.MANAGER),
        auditor_id=uuid4(),
        backroom_id=uuid4(),
        shelf_id=uuid4(),
        first_sku_id=uuid4(),
        second_sku_id=uuid4(),
        newest_line_id=uuid4(),
        older_line_id=uuid4(),
        match_line_id=uuid4(),
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    now = datetime.now(UTC)
    with factory.begin() as session:
        session.add_all(
            [
                User(
                    id=fixture.manager.user_id,
                    login_identifier=fixture.manager.login_identifier,
                    password_hash="test-only",
                    role=fixture.manager.role.value,
                ),
                User(
                    id=fixture.auditor_id,
                    login_identifier="audit.staff",
                    password_hash="test-only",
                    role=Role.WAREHOUSE_STAFF.value,
                ),
                Warehouse(id=fixture.warehouse_id, code=f"W-{uuid4().hex}"),
                Sku(id=fixture.first_sku_id, code=f"SKU-A-{uuid4().hex}"),
                Sku(id=fixture.second_sku_id, code=f"SKU-B-{uuid4().hex}"),
            ]
        )
        session.flush()
        session.add_all(
            [
                InternalLocation(
                    id=fixture.backroom_id,
                    warehouse_id=fixture.warehouse_id,
                    code="BACKROOM",
                ),
                InternalLocation(
                    id=fixture.shelf_id,
                    warehouse_id=fixture.warehouse_id,
                    code="SALES_SHELF",
                ),
            ]
        )
        session.flush()
        newest_audit = AuditSession(
            warehouse_id=fixture.warehouse_id,
            scope_type="SELECTED_PAIRS",
            result="MISMATCH",
            status="MISMATCH_RECORDED",
            audited_by_user_id=fixture.auditor_id,
            audited_at=now,
            idempotency_key=f"source-new-{uuid4().hex}",
            request_fingerprint="a" * 64,
        )
        older_audit = AuditSession(
            warehouse_id=fixture.warehouse_id,
            scope_type="SELECTED_PAIRS",
            result="MISMATCH",
            status="MISMATCH_RECORDED",
            audited_by_user_id=fixture.auditor_id,
            audited_at=now - timedelta(hours=1),
            idempotency_key=f"source-old-{uuid4().hex}",
            request_fingerprint="b" * 64,
        )
        match_audit = AuditSession(
            warehouse_id=fixture.warehouse_id,
            scope_type="SELECTED_PAIRS",
            result="MATCH",
            status="MATCH_COMPLETED",
            audited_by_user_id=fixture.auditor_id,
            audited_at=now - timedelta(hours=2),
            idempotency_key=f"source-match-{uuid4().hex}",
            request_fingerprint="c" * 64,
        )
        session.add_all([newest_audit, older_audit, match_audit])
        session.flush()
        session.add_all(
            [
                AuditLine(
                    id=fixture.newest_line_id,
                    audit_id=newest_audit.id,
                    sku_id=fixture.first_sku_id,
                    location_id=fixture.backroom_id,
                    system_quantity=12,
                    physical_quantity=10,
                    quantity_discrepancy=-2,
                    result="MISMATCH",
                ),
                AuditLine(
                    id=fixture.older_line_id,
                    audit_id=older_audit.id,
                    sku_id=fixture.second_sku_id,
                    location_id=fixture.shelf_id,
                    system_quantity=0,
                    physical_quantity=3,
                    quantity_discrepancy=3,
                    result="MISMATCH",
                ),
                AuditLine(
                    id=fixture.match_line_id,
                    audit_id=match_audit.id,
                    sku_id=fixture.first_sku_id,
                    location_id=fixture.shelf_id,
                    system_quantity=6,
                    physical_quantity=6,
                    quantity_discrepancy=0,
                    result="MATCH",
                ),
                StockBalance(
                    sku_id=fixture.first_sku_id,
                    location_id=fixture.backroom_id,
                    quantity=11,
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
    app.dependency_overrides[get_actor] = lambda: fixture.manager
    with TestClient(app) as client:
        yield client, factory, fixture
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def post_recheck(
    client: TestClient,
    line_id: UUID,
    quantity: object,
    key: str | None = "recheck-key",
):
    headers = {} if key is None else {"Idempotency-Key": key}
    return client.post(
        f"/api/v1/audit-discrepancies/{line_id}/rechecks",
        json={"recheck_physical_quantity": quantity},
        headers=headers,
    )


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


def original_snapshot(
    factory: sessionmaker[Session],
) -> tuple[list[object], list[object]]:
    with factory() as session:
        sessions = list(
            session.execute(
                select(
                    AuditSession.id,
                    AuditSession.result,
                    AuditSession.status,
                    AuditSession.audited_at,
                ).order_by(AuditSession.id)
            ).all()
        )
        lines = list(
            session.execute(
                select(
                    AuditLine.id,
                    AuditLine.system_quantity,
                    AuditLine.physical_quantity,
                    AuditLine.quantity_discrepancy,
                    AuditLine.result,
                ).order_by(AuditLine.id)
            ).all()
        )
        return sessions, lines


def neighboring_counts(factory: sessionmaker[Session]) -> tuple[int, ...]:
    with factory() as session:
        return tuple(
            int(session.scalar(select(func.count(model.id))) or 0)
            for model in (Receive, PutawayAllocation, PickAllocation, Transfer)
        )


def test_list_is_mismatch_only_ordered_and_does_not_read_current_stock(
    recheck_api,
) -> None:
    client, factory, fixture = recheck_api
    before = stock_snapshot(factory)
    response = client.get("/api/v1/audit-discrepancies")
    assert response.status_code == 200
    body = response.json()
    assert [item["audit_line_id"] for item in body["items"]] == [
        str(fixture.newest_line_id),
        str(fixture.older_line_id),
    ]
    item = body["items"][0]
    assert item["original"] == {
        "system_quantity": 12,
        "physical_quantity": 10,
        "quantity_discrepancy": -2,
        "result": "MISMATCH",
        "audited_by": {
            "user_id": str(fixture.auditor_id),
            "login_identifier": "audit.staff",
        },
        "audited_at": item["original"]["audited_at"],
    }
    assert item["recheck"] is None
    assert item["adjust_eligible"] is False
    assert "idempotency_key" not in str(body)
    assert "request_fingerprint" not in str(body)
    assert stock_snapshot(factory) == before


def test_empty_list(recheck_api) -> None:
    client, factory, _fixture = recheck_api
    with factory.begin() as session:
        session.query(AuditLine).delete()
        session.query(AuditSession).delete()
    response = client.get("/api/v1/audit-discrepancies")
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_detail_and_unknown_or_match_line(recheck_api) -> None:
    client, _factory, fixture = recheck_api
    detail = client.get(f"/api/v1/audit-discrepancies/{fixture.newest_line_id}")
    assert detail.status_code == 200
    assert detail.json()["audit_line_id"] == str(fixture.newest_line_id)
    for line_id in (fixture.match_line_id, uuid4()):
        response = client.get(f"/api/v1/audit-discrepancies/{line_id}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "AUDIT_DISCREPANCY_NOT_FOUND"


def test_recheck_match_snapshots_current_stock_and_has_no_other_effect(
    recheck_api,
) -> None:
    client, factory, fixture = recheck_api
    stock_before = stock_snapshot(factory)
    original_before = original_snapshot(factory)
    neighbors_before = neighboring_counts(factory)
    response = post_recheck(client, fixture.newest_line_id, 11, "match-key")
    assert response.status_code == 201
    body = response.json()
    assert body["recheck_system_quantity"] == 11
    assert body["recheck_physical_quantity"] == 11
    assert body["recheck_quantity_discrepancy"] == 0
    assert body["result"] == "MATCH"
    assert body["adjust_eligible"] is False
    assert stock_snapshot(factory) == stock_before
    assert original_snapshot(factory) == original_before
    assert neighboring_counts(factory) == neighbors_before
    detail = client.get(f"/api/v1/audit-discrepancies/{fixture.newest_line_id}")
    assert detail.json()["recheck"]["result"] == "MATCH"
    assert detail.json()["adjust_eligible"] is False
    listed = client.get("/api/v1/audit-discrepancies").json()["items"]
    assert listed[0]["recheck"]["result"] == "MATCH"


def test_missing_balance_is_zero_without_creating_one_and_mismatch_is_eligible(
    recheck_api,
) -> None:
    client, factory, fixture = recheck_api
    before = stock_snapshot(factory)
    response = post_recheck(client, fixture.older_line_id, 3, "missing-key")
    assert response.status_code == 201
    body = response.json()
    assert body["recheck_system_quantity"] == 0
    assert body["recheck_quantity_discrepancy"] == 3
    assert body["result"] == "MISMATCH"
    assert body["adjust_eligible"] is True
    assert stock_snapshot(factory) == before
    detail = client.get(f"/api/v1/audit-discrepancies/{fixture.older_line_id}")
    assert detail.status_code == 200
    assert detail.json()["recheck"]["result"] == "MISMATCH"
    assert detail.json()["adjust_eligible"] is True


def test_negative_recheck_discrepancy(recheck_api) -> None:
    client, _factory, fixture = recheck_api
    response = post_recheck(client, fixture.newest_line_id, 9, "negative-key")
    assert response.status_code == 201
    assert response.json()["recheck_quantity_discrepancy"] == -2
    assert response.json()["result"] == "MISMATCH"


def test_zero_physical_quantity_is_valid(recheck_api) -> None:
    client, _factory, fixture = recheck_api
    response = post_recheck(client, fixture.older_line_id, 0, "zero-key")
    assert response.status_code == 201
    assert response.json()["result"] == "MATCH"
    assert response.json()["recheck_quantity_discrepancy"] == 0


def test_replay_preserves_historical_snapshot_after_stock_change(recheck_api) -> None:
    client, factory, fixture = recheck_api
    first = post_recheck(client, fixture.newest_line_id, 11, "replay-key")
    assert first.status_code == 201
    with factory.begin() as session:
        balance = session.scalar(
            select(StockBalance).where(
                StockBalance.sku_id == fixture.first_sku_id,
                StockBalance.location_id == fixture.backroom_id,
            )
        )
        assert balance is not None
        balance.quantity = 7
    replay = post_recheck(client, fixture.newest_line_id, 11, "replay-key")
    assert replay.status_code == 200
    assert replay.json() == first.json()


def test_key_reuse_and_second_key_are_typed(recheck_api) -> None:
    client, _factory, fixture = recheck_api
    first = post_recheck(client, fixture.newest_line_id, 11, "first-key")
    assert first.status_code == 201
    reused = post_recheck(client, fixture.newest_line_id, 10, "first-key")
    assert reused.status_code == 409
    assert reused.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    second = post_recheck(client, fixture.newest_line_id, 11, "second-key")
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "RECHECK_ALREADY_RECORDED"


@pytest.mark.parametrize("quantity", [True, "1", 1.5, -1, 2_147_483_648])
def test_strict_quantity_validation_is_typed(recheck_api, quantity: object) -> None:
    client, _factory, fixture = recheck_api
    response = post_recheck(
        client, fixture.newest_line_id, quantity, "invalid-quantity"
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_RECHECK_QUANTITY"


@pytest.mark.parametrize("key", [None, "", "   ", "x" * 256])
def test_invalid_idempotency_key_is_typed(recheck_api, key: str | None) -> None:
    client, _factory, fixture = recheck_api
    response = post_recheck(client, fixture.newest_line_id, 11, key)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_IDEMPOTENCY_KEY"


def test_match_line_cannot_be_rechecked(recheck_api) -> None:
    client, _factory, fixture = recheck_api
    response = post_recheck(client, fixture.match_line_id, 6, "match-line")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "AUDIT_DISCREPANCY_NOT_ELIGIBLE"


def test_unknown_line_cannot_be_rechecked(recheck_api) -> None:
    client, _factory, _fixture = recheck_api
    response = post_recheck(client, uuid4(), 0, "unknown-line")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "AUDIT_DISCREPANCY_NOT_FOUND"


@pytest.mark.parametrize("role", [Role.WAREHOUSE_STAFF, Role.PURCHASING, Role.ADMIN])
def test_wrong_roles_are_forbidden(recheck_api, role: Role) -> None:
    client, factory, fixture = recheck_api
    app.dependency_overrides[get_actor] = lambda: Actor(uuid4(), "wrong.role", role)
    assert client.get("/api/v1/audit-discrepancies").status_code == 403
    assert (
        client.get(f"/api/v1/audit-discrepancies/{fixture.newest_line_id}").status_code
        == 403
    )
    forbidden = post_recheck(client, fixture.newest_line_id, 11, "forbidden")
    assert forbidden.status_code == 403
    with factory() as session:
        assert session.scalar(select(func.count(AuditRecheck.id))) == 0


def test_unauthenticated_is_rejected(recheck_api) -> None:
    client, _factory, fixture = recheck_api
    del app.dependency_overrides[get_actor]
    assert client.get("/api/v1/audit-discrepancies").status_code == 401
    assert (
        client.get(f"/api/v1/audit-discrepancies/{fixture.newest_line_id}").status_code
        == 401
    )
    assert post_recheck(client, fixture.newest_line_id, 11, "unauth").status_code == 401


def test_foreign_warehouse_discrepancy_is_hidden(
    recheck_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, factory, fixture = recheck_api
    foreign_warehouse_id = uuid4()
    foreign_location_id = uuid4()
    foreign_line_id = uuid4()
    with factory.begin() as session:
        foreign = Warehouse(id=foreign_warehouse_id, code=f"FOREIGN-{uuid4().hex}")
        session.add(foreign)
        session.flush()
        session.add(
            InternalLocation(
                id=foreign_location_id,
                warehouse_id=foreign.id,
                code="BACKROOM",
            )
        )
        session.flush()
        audit = AuditSession(
            warehouse_id=foreign.id,
            scope_type="SELECTED_PAIRS",
            result="MISMATCH",
            status="MISMATCH_RECORDED",
            audited_by_user_id=fixture.auditor_id,
            audited_at=datetime.now(UTC),
            idempotency_key=f"foreign-{uuid4().hex}",
            request_fingerprint="f" * 64,
        )
        session.add(audit)
        session.flush()
        session.add(
            AuditLine(
                id=foreign_line_id,
                audit_id=audit.id,
                sku_id=fixture.first_sku_id,
                location_id=foreign_location_id,
                system_quantity=1,
                physical_quantity=0,
                quantity_discrepancy=-1,
                result="MISMATCH",
            )
        )
    monkeypatch.setattr(
        "warehouse_api.audit_discrepancy._canonical_warehouse_id",
        lambda _session: fixture.warehouse_id,
    )
    hidden = client.get(f"/api/v1/audit-discrepancies/{foreign_line_id}")
    assert hidden.status_code == 404
    response = post_recheck(client, foreign_line_id, 0, "foreign-key")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "AUDIT_DISCREPANCY_NOT_FOUND"


def test_failure_after_insert_rolls_back(recheck_api, monkeypatch) -> None:
    client, factory, fixture = recheck_api

    def fail_response(*_args, **_kwargs):
        raise RuntimeError("forced response failure")

    monkeypatch.setattr(
        "warehouse_api.audit_discrepancy._response_for_recheck", fail_response
    )
    with pytest.raises(RuntimeError, match="forced response failure"):
        post_recheck(client, fixture.newest_line_id, 11, "rollback-key")
    with factory() as session:
        assert session.scalar(select(func.count(AuditRecheck.id))) == 0
