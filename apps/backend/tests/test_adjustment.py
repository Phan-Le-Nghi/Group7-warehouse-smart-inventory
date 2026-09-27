from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session, sessionmaker

from warehouse_api.auth import Actor, Role, get_actor
from warehouse_api.main import app
from warehouse_api.models import (
    AdjustRequest,
    AuditLine,
    AuditRecheck,
    AuditSession,
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
class AdjustmentFixture:
    warehouse_id: UUID
    staff: Actor
    manager: Actor
    negative_recheck_id: UUID
    positive_recheck_id: UUID
    match_recheck_id: UUID
    sku_id: UUID
    location_id: UUID


def _add_audit_case(
    session: Session,
    *,
    warehouse_id: UUID,
    sku_id: UUID,
    location_id: UUID,
    auditor_id: UUID,
    manager_id: UUID,
    audit_system: int,
    audit_physical: int,
    recheck_system: int,
    recheck_physical: int,
) -> UUID:
    audit_discrepancy = audit_physical - audit_system
    audit = AuditSession(
        warehouse_id=warehouse_id,
        scope_type="SELECTED_PAIRS",
        result="MISMATCH",
        status="MISMATCH_RECORDED",
        audited_by_user_id=auditor_id,
        audited_at=datetime.now(UTC),
        idempotency_key=f"audit-{uuid4().hex}",
        request_fingerprint="a" * 64,
    )
    session.add(audit)
    session.flush()
    line = AuditLine(
        audit_id=audit.id,
        sku_id=sku_id,
        location_id=location_id,
        system_quantity=audit_system,
        physical_quantity=audit_physical,
        quantity_discrepancy=audit_discrepancy,
        result="MISMATCH",
    )
    session.add(line)
    session.flush()
    recheck_discrepancy = recheck_physical - recheck_system
    recheck = AuditRecheck(
        audit_line_id=line.id,
        recheck_system_quantity=recheck_system,
        recheck_physical_quantity=recheck_physical,
        recheck_quantity_discrepancy=recheck_discrepancy,
        result="MATCH" if recheck_discrepancy == 0 else "MISMATCH",
        performed_by_user_id=manager_id,
        performed_at=datetime.now(UTC),
        idempotency_key=f"recheck-{uuid4().hex}",
        request_fingerprint="b" * 64,
    )
    session.add(recheck)
    session.flush()
    return recheck.id


@pytest.fixture
def adjustment_api(api_client: TestClient, session_factory: sessionmaker[Session]):
    warehouse_id = uuid4()
    staff = Actor(uuid4(), "adjust.staff", Role.WAREHOUSE_STAFF)
    manager = Actor(uuid4(), "adjust.manager", Role.MANAGER)
    sku_id = uuid4()
    location_id = uuid4()
    with session_factory.begin() as session:
        session.add_all(
            [
                User(
                    id=staff.user_id,
                    login_identifier=staff.login_identifier,
                    password_hash="test-only",
                    role=staff.role.value,
                ),
                User(
                    id=manager.user_id,
                    login_identifier=manager.login_identifier,
                    password_hash="test-only",
                    role=manager.role.value,
                ),
                Warehouse(id=warehouse_id, code="MAIN"),
                Sku(id=sku_id, code="ADJUST-SKU"),
            ]
        )
        session.flush()
        session.add(
            InternalLocation(
                id=location_id,
                warehouse_id=warehouse_id,
                code="BACKROOM",
            )
        )
        session.flush()
        negative_id = _add_audit_case(
            session,
            warehouse_id=warehouse_id,
            sku_id=sku_id,
            location_id=location_id,
            auditor_id=staff.user_id,
            manager_id=manager.user_id,
            audit_system=12,
            audit_physical=10,
            recheck_system=10,
            recheck_physical=8,
        )
        positive_id = _add_audit_case(
            session,
            warehouse_id=warehouse_id,
            sku_id=sku_id,
            location_id=location_id,
            auditor_id=staff.user_id,
            manager_id=manager.user_id,
            audit_system=8,
            audit_physical=10,
            recheck_system=10,
            recheck_physical=13,
        )
        match_id = _add_audit_case(
            session,
            warehouse_id=warehouse_id,
            sku_id=sku_id,
            location_id=location_id,
            auditor_id=staff.user_id,
            manager_id=manager.user_id,
            audit_system=9,
            audit_physical=8,
            recheck_system=10,
            recheck_physical=10,
        )
        session.add(StockBalance(sku_id=sku_id, location_id=location_id, quantity=99))
    fixture = AdjustmentFixture(
        warehouse_id=warehouse_id,
        staff=staff,
        manager=manager,
        negative_recheck_id=negative_id,
        positive_recheck_id=positive_id,
        match_recheck_id=match_id,
        sku_id=sku_id,
        location_id=location_id,
    )
    app.dependency_overrides[get_actor] = lambda: staff
    yield api_client, session_factory, fixture
    app.dependency_overrides.pop(get_actor, None)


def _post(
    client: TestClient,
    recheck_id: UUID,
    reason: object = "Count confirmed",
    key: str | None = "adjust-key",
    **extra: object,
):
    headers = {} if key is None else {"Idempotency-Key": key}
    return client.post(
        "/api/v1/adjustments",
        json={"audit_recheck_id": str(recheck_id), "reason": reason, **extra},
        headers=headers,
    )


def _business_snapshot(factory: sessionmaker[Session]) -> tuple[object, ...]:
    with factory() as session:
        stock = list(
            session.execute(
                select(
                    StockBalance.id,
                    StockBalance.sku_id,
                    StockBalance.location_id,
                    StockBalance.quantity,
                ).order_by(StockBalance.id)
            ).all()
        )
        audits = list(
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
        rechecks = list(
            session.execute(
                select(
                    AuditRecheck.id,
                    AuditRecheck.recheck_system_quantity,
                    AuditRecheck.recheck_physical_quantity,
                    AuditRecheck.recheck_quantity_discrepancy,
                    AuditRecheck.result,
                    AuditRecheck.performed_at,
                ).order_by(AuditRecheck.id)
            ).all()
        )
        neighbors = tuple(
            int(session.scalar(select(func.count(model.id))) or 0)
            for model in (Receive, PutawayAllocation, PickAllocation, Transfer)
        )
        return stock, audits, lines, rechecks, neighbors


def test_context_derives_negative_and_positive_changes(adjustment_api) -> None:
    client, _factory, fixture = adjustment_api
    negative = client.get(f"/api/v1/adjustments/context/{fixture.negative_recheck_id}")
    assert negative.status_code == 200
    assert negative.json()["requested_change"] == -2
    assert negative.json()["recheck"] == {
        "recheck_system_quantity": 10,
        "recheck_physical_quantity": 8,
        "recheck_quantity_discrepancy": -2,
        "result": "MISMATCH",
        "performed_at": negative.json()["recheck"]["performed_at"],
    }
    assert negative.json()["existing_adjustment"] is None
    positive = client.get(f"/api/v1/adjustments/context/{fixture.positive_recheck_id}")
    assert positive.status_code == 200
    assert positive.json()["requested_change"] == 3


def test_context_blocks_match_unknown_and_foreign_warehouse(
    adjustment_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, factory, fixture = adjustment_api
    match = client.get(f"/api/v1/adjustments/context/{fixture.match_recheck_id}")
    assert match.status_code == 409
    assert match.json()["error"]["code"] == "ADJUSTMENT_NOT_ELIGIBLE"
    match_create = _post(client, fixture.match_recheck_id, key="match-create")
    assert match_create.status_code == 409
    assert match_create.json()["error"]["code"] == "ADJUSTMENT_NOT_ELIGIBLE"
    unknown = client.get(f"/api/v1/adjustments/context/{uuid4()}")
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "AUDIT_RECHECK_NOT_FOUND"
    unknown_create = _post(client, uuid4(), key="unknown-create")
    assert unknown_create.status_code == 404
    assert unknown_create.json()["error"]["code"] == "AUDIT_RECHECK_NOT_FOUND"

    foreign_warehouse_id = uuid4()
    foreign_location_id = uuid4()
    with factory.begin() as session:
        session.add(Warehouse(id=foreign_warehouse_id, code="FOREIGN"))
        session.flush()
        session.add(
            InternalLocation(
                id=foreign_location_id,
                warehouse_id=foreign_warehouse_id,
                code="BACKROOM",
            )
        )
        session.flush()
        foreign_recheck_id = _add_audit_case(
            session,
            warehouse_id=foreign_warehouse_id,
            sku_id=fixture.sku_id,
            location_id=foreign_location_id,
            auditor_id=fixture.staff.user_id,
            manager_id=fixture.manager.user_id,
            audit_system=2,
            audit_physical=1,
            recheck_system=2,
            recheck_physical=1,
        )
    monkeypatch.setattr(
        "warehouse_api.adjustment._canonical_warehouse_id",
        lambda _session: fixture.warehouse_id,
    )
    hidden = client.get(f"/api/v1/adjustments/context/{foreign_recheck_id}")
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "AUDIT_RECHECK_NOT_FOUND"
    hidden_create = _post(client, foreign_recheck_id, key="foreign-create")
    assert hidden_create.status_code == 404
    assert hidden_create.json()["error"]["code"] == "AUDIT_RECHECK_NOT_FOUND"


def test_create_persists_normalized_source_snapshots_and_no_other_effect(
    adjustment_api,
) -> None:
    client, factory, fixture = adjustment_api
    before = _business_snapshot(factory)
    statements: list[str] = []
    engine = factory.kw["bind"]

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.lower())

    event.listen(engine, "before_cursor_execute", capture)
    try:
        response = _post(
            client,
            fixture.negative_recheck_id,
            "  Count confirmed after recheck  ",
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert response.status_code == 201
    body = response.json()
    assert body["recheck_system_quantity_snapshot"] == 10
    assert body["recheck_physical_quantity_snapshot"] == 8
    assert body["requested_change"] == -2
    assert body["reason"] == "Count confirmed after recheck"
    assert body["status"] == "PENDING_MANAGER_DECISION"
    assert all("stock_balances" not in statement for statement in statements)
    assert _business_snapshot(factory) == before
    with factory() as session:
        request = session.scalar(select(AdjustRequest))
        assert request is not None
        assert request.sku_id == fixture.sku_id
        assert request.location_id == fixture.location_id


def test_create_persists_positive_requested_change(adjustment_api) -> None:
    client, _factory, fixture = adjustment_api
    response = _post(
        client,
        fixture.positive_recheck_id,
        "Confirmed positive discrepancy",
        "positive-key",
    )
    assert response.status_code == 201
    assert response.json()["recheck_system_quantity_snapshot"] == 10
    assert response.json()["recheck_physical_quantity_snapshot"] == 13
    assert response.json()["requested_change"] == 3


@pytest.mark.parametrize(
    ("reason", "expected_status"),
    [(" ", 422), ("x" * 500, 201), ("x" * 501, 422)],
)
def test_reason_boundaries(adjustment_api, reason: str, expected_status: int) -> None:
    client, _factory, fixture = adjustment_api
    response = _post(client, fixture.negative_recheck_id, reason)
    assert response.status_code == expected_status
    if expected_status == 422:
        assert response.json()["error"]["code"] == "INVALID_REASON"


def test_missing_reason_and_authoritative_extra_fields_are_rejected(
    adjustment_api,
) -> None:
    client, _factory, fixture = adjustment_api
    missing = client.post(
        "/api/v1/adjustments",
        json={"audit_recheck_id": str(fixture.negative_recheck_id)},
        headers={"Idempotency-Key": "missing-reason"},
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "INVALID_REASON"
    extra = _post(
        client,
        fixture.negative_recheck_id,
        key="extra-field",
        requested_change=999,
    )
    assert extra.status_code == 422
    assert extra.json()["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize("key", [None, "", "   ", "x" * 256])
def test_invalid_idempotency_key_is_typed(adjustment_api, key: str | None) -> None:
    client, _factory, fixture = adjustment_api
    response = _post(client, fixture.negative_recheck_id, key=key)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_IDEMPOTENCY_KEY"


def test_replay_preserves_historical_response_and_context_summary(
    adjustment_api,
) -> None:
    client, factory, fixture = adjustment_api
    first = _post(client, fixture.negative_recheck_id, "  Stable reason  ", "same-key")
    assert first.status_code == 201
    with factory.begin() as session:
        balance = session.scalar(select(StockBalance))
        assert balance is not None
        balance.quantity = 1
    replay = _post(client, fixture.negative_recheck_id, "Stable reason", "same-key")
    assert replay.status_code == 200
    assert replay.json() == first.json()
    context = client.get(f"/api/v1/adjustments/context/{fixture.negative_recheck_id}")
    assert context.status_code == 200
    summary = context.json()["existing_adjustment"]
    assert summary["adjustment_id"] == first.json()["adjustment_id"]
    assert summary["reason"] == "Stable reason"
    assert "idempotency_key" not in summary
    assert "request_fingerprint" not in summary


def test_duplicate_conflicts_are_typed(adjustment_api) -> None:
    client, _factory, fixture = adjustment_api
    first = _post(client, fixture.negative_recheck_id, "First", "first-key")
    assert first.status_code == 201
    reused = _post(client, fixture.negative_recheck_id, "Different", "first-key")
    assert reused.status_code == 409
    assert reused.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    duplicate = _post(client, fixture.negative_recheck_id, "First", "second-key")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "ADJUSTMENT_ALREADY_EXISTS"


@pytest.mark.parametrize("role", [Role.MANAGER, Role.PURCHASING, Role.ADMIN])
def test_wrong_roles_are_forbidden(adjustment_api, role: Role) -> None:
    client, factory, fixture = adjustment_api
    app.dependency_overrides[get_actor] = lambda: Actor(uuid4(), "wrong.role", role)
    context = client.get(f"/api/v1/adjustments/context/{fixture.negative_recheck_id}")
    create = _post(client, fixture.negative_recheck_id, key=f"key-{role}")
    assert context.status_code == 403
    assert create.status_code == 403
    with factory() as session:
        assert session.scalar(select(func.count(AdjustRequest.id))) == 0


def test_unauthenticated_is_rejected(adjustment_api) -> None:
    client, _factory, fixture = adjustment_api
    app.dependency_overrides.pop(get_actor, None)
    context = client.get(f"/api/v1/adjustments/context/{fixture.negative_recheck_id}")
    create = _post(client, fixture.negative_recheck_id, key="unauthenticated")
    assert context.status_code == 401
    assert create.status_code == 401


def test_failure_after_insert_rolls_back(adjustment_api, monkeypatch) -> None:
    client, factory, fixture = adjustment_api

    def fail_response(*_args, **_kwargs):
        raise RuntimeError("forced response failure")

    monkeypatch.setattr(
        "warehouse_api.adjustment._response_for_adjustment", fail_response
    )
    with pytest.raises(RuntimeError, match="forced response failure"):
        _post(client, fixture.negative_recheck_id, key="rollback-key")
    with factory() as session:
        assert session.scalar(select(func.count(AdjustRequest.id))) == 0
