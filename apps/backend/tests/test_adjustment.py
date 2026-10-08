from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import set_committed_value

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


def test_eligible_queue_is_ordered_derived_read_only_and_excludes_ineligible(
    adjustment_api,
) -> None:
    client, factory, fixture = adjustment_api
    older = datetime(2026, 9, 27, 8, 0, tzinfo=UTC)
    newer = datetime(2026, 9, 27, 9, 0, tzinfo=UTC)
    with factory.begin() as session:
        session.get(AuditRecheck, fixture.negative_recheck_id).performed_at = older
        session.get(AuditRecheck, fixture.positive_recheck_id).performed_at = newer

    before = _business_snapshot(factory)
    with factory() as session:
        request_count = session.scalar(select(func.count(AdjustRequest.id)))

    response = client.get("/api/v1/adjustments/eligible-rechecks")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["audit_recheck_id"] for item in items] == [
        str(fixture.positive_recheck_id),
        str(fixture.negative_recheck_id),
    ]
    assert items[0] == {
        "audit_recheck_id": str(fixture.positive_recheck_id),
        "sku": {"id": str(fixture.sku_id), "code": "ADJUST-SKU"},
        "location": {"id": str(fixture.location_id), "code": "BACKROOM"},
        "recheck_system_quantity": 10,
        "recheck_physical_quantity": 13,
        "requested_change": 3,
        "rechecked_at": items[0]["rechecked_at"],
    }
    assert items[1]["requested_change"] == -2
    assert str(fixture.match_recheck_id) not in {
        item["audit_recheck_id"] for item in items
    }
    assert _business_snapshot(factory) == before
    with factory() as session:
        assert session.scalar(select(func.count(AdjustRequest.id))) == request_count

    created = _post(client, fixture.negative_recheck_id, key="queue-exclusion")
    assert created.status_code == 201
    remaining = client.get("/api/v1/adjustments/eligible-rechecks").json()["items"]
    assert [item["audit_recheck_id"] for item in remaining] == [
        str(fixture.positive_recheck_id)
    ]


@pytest.mark.parametrize("role", [Role.MANAGER, Role.PURCHASING, Role.ADMIN])
def test_eligible_queue_forbids_non_staff(adjustment_api, role: Role) -> None:
    client, factory, _fixture = adjustment_api
    app.dependency_overrides[get_actor] = lambda: Actor(uuid4(), "wrong.role", role)
    before = _business_snapshot(factory)
    with factory() as session:
        request_count = session.scalar(select(func.count(AdjustRequest.id)))

    response = client.get("/api/v1/adjustments/eligible-rechecks")

    assert response.status_code == 403
    assert _business_snapshot(factory) == before
    with factory() as session:
        assert session.scalar(select(func.count(AdjustRequest.id))) == request_count


def test_eligible_queue_rejects_unauthenticated(adjustment_api) -> None:
    client, _factory, _fixture = adjustment_api
    app.dependency_overrides.pop(get_actor, None)
    assert client.get("/api/v1/adjustments/eligible-rechecks").status_code == 401


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


def _decide(
    client: TestClient,
    adjustment_id: str,
    decision: str,
    key: str = "decision-key",
    rejection_reason: str | None = None,
):
    payload: dict[str, object] = {"decision": decision}
    if rejection_reason is not None:
        payload["rejection_reason"] = rejection_reason
    return client.post(
        f"/api/v1/adjustments/{adjustment_id}/decision",
        json=payload,
        headers={"Idempotency-Key": key},
    )


def test_manager_list_detail_and_approve_apply_exactly_once(adjustment_api) -> None:
    client, factory, fixture = adjustment_api
    created = _post(client, fixture.negative_recheck_id, key="create-for-approve")
    adjustment_id = created.json()["adjustment_id"]
    with factory.begin() as session:
        balance = session.scalar(select(StockBalance))
        assert balance is not None
        balance.quantity = 10
    app.dependency_overrides[get_actor] = lambda: fixture.manager

    queue = client.get("/api/v1/adjustments?status=PENDING_MANAGER_DECISION")
    assert queue.status_code == 200
    assert queue.json()["items"][0]["adjustment_id"] == adjustment_id
    detail = client.get(f"/api/v1/adjustments/{adjustment_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "PENDING_MANAGER_DECISION"
    assert "decision_idempotency_key" not in detail.json()

    approved = _decide(client, adjustment_id, "APPROVE")
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPLIED"
    assert approved.json()["applied_stock_before"] == 10
    assert approved.json()["applied_stock_after"] == 8
    replay = _decide(client, adjustment_id, "APPROVE")
    assert replay.status_code == 200
    assert replay.json() == approved.json()
    with factory() as session:
        assert session.scalar(select(StockBalance.quantity)) == 8


def test_reject_normalizes_reason_and_never_queries_stock(adjustment_api) -> None:
    client, factory, fixture = adjustment_api
    created = _post(client, fixture.negative_recheck_id, key="create-for-reject")
    adjustment_id = created.json()["adjustment_id"]
    app.dependency_overrides[get_actor] = lambda: fixture.manager
    statements: list[str] = []
    engine = factory.kw["bind"]

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.lower())

    event.listen(engine, "before_cursor_execute", capture)
    try:
        rejected = _decide(
            client,
            adjustment_id,
            "REJECT",
            key="reject-key",
            rejection_reason="  Evidence is not accepted  ",
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    assert rejected.json()["rejection_reason"] == "Evidence is not accepted"
    assert all("stock_balances" not in statement for statement in statements)


def test_stale_and_negative_approval_leave_request_pending(adjustment_api) -> None:
    client, factory, fixture = adjustment_api
    stale_created = _post(client, fixture.negative_recheck_id, key="stale-create")
    stale_id = stale_created.json()["adjustment_id"]
    app.dependency_overrides[get_actor] = lambda: fixture.manager
    stale = _decide(client, stale_id, "APPROVE", key="stale-decision")
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "ADJUSTMENT_STALE"
    with factory() as session:
        request = session.get(AdjustRequest, UUID(stale_id))
        assert request is not None
        assert request.status == "PENDING_MANAGER_DECISION"
        assert request.decided_at is None


def test_defensive_negative_candidate_leaves_request_pending(
    adjustment_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, factory, fixture = adjustment_api
    created = _post(client, fixture.negative_recheck_id, key="negative-create")
    adjustment_id = created.json()["adjustment_id"]
    with factory.begin() as session:
        balance = session.scalar(select(StockBalance))
        assert balance is not None
        balance.quantity = 10

    def force_defensive_branch(adjustment, *_args):
        set_committed_value(adjustment, "requested_change", -11)

    monkeypatch.setattr(
        "warehouse_api.adjustment._validate_immutable_source",
        force_defensive_branch,
    )
    app.dependency_overrides[get_actor] = lambda: fixture.manager
    response = _decide(client, adjustment_id, "APPROVE", key="negative-decision")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_STOCK_FOR_ADJUSTMENT"
    with factory() as session:
        request = session.get(AdjustRequest, UUID(adjustment_id))
        assert request is not None
        assert request.status == "PENDING_MANAGER_DECISION"
        assert request.requested_change == -2
        assert session.scalar(select(StockBalance.quantity)) == 10


def test_staff_replay_and_context_report_current_terminal_status(
    adjustment_api,
) -> None:
    client, factory, fixture = adjustment_api
    created = _post(
        client,
        fixture.negative_recheck_id,
        reason="Stable creation intent",
        key="staff-terminal-replay",
    )
    adjustment_id = created.json()["adjustment_id"]
    app.dependency_overrides[get_actor] = lambda: fixture.manager
    rejected = _decide(
        client,
        adjustment_id,
        "REJECT",
        key="manager-reject",
        rejection_reason="Rejected after review",
    )
    assert rejected.status_code == 200

    app.dependency_overrides[get_actor] = lambda: fixture.staff
    context = client.get(f"/api/v1/adjustments/context/{fixture.negative_recheck_id}")
    assert context.json()["existing_adjustment"]["status"] == "REJECTED"
    replay = _post(
        client,
        fixture.negative_recheck_id,
        reason="Stable creation intent",
        key="staff-terminal-replay",
    )
    assert replay.status_code == 200
    assert replay.json()["status"] == "REJECTED"
    with factory() as session:
        assert session.scalar(select(func.count(AdjustRequest.id))) == 1


def test_missing_zero_balance_positive_adjustment_applies(adjustment_api) -> None:
    client, factory, fixture = adjustment_api
    with factory.begin() as session:
        positive_from_zero = _add_audit_case(
            session,
            warehouse_id=fixture.warehouse_id,
            sku_id=fixture.sku_id,
            location_id=fixture.location_id,
            auditor_id=fixture.staff.user_id,
            manager_id=fixture.manager.user_id,
            audit_system=0,
            audit_physical=3,
            recheck_system=0,
            recheck_physical=3,
        )
        balance = session.scalar(select(StockBalance))
        assert balance is not None
        session.delete(balance)
    created = _post(client, positive_from_zero, key="missing-zero-create")
    app.dependency_overrides[get_actor] = lambda: fixture.manager
    approved = _decide(
        client,
        created.json()["adjustment_id"],
        "APPROVE",
        key="missing-zero-decision",
    )
    assert approved.status_code == 200
    assert approved.json()["applied_stock_before"] == 0
    assert approved.json()["applied_stock_after"] == 3
    with factory() as session:
        assert session.scalar(select(StockBalance.quantity)) == 3


@pytest.mark.parametrize(
    ("decision", "reason"),
    [
        ("REJECT", None),
        ("REJECT", "   "),
        ("REJECT", "x" * 501),
        ("APPROVE", "not allowed"),
    ],
)
def test_decision_rejection_reason_validation(
    adjustment_api, decision: str, reason: str | None
) -> None:
    client, _factory, fixture = adjustment_api
    created = _post(client, fixture.negative_recheck_id, key="validation-create")
    app.dependency_overrides[get_actor] = lambda: fixture.manager
    response = _decide(
        client,
        created.json()["adjustment_id"],
        decision,
        key="validation-decision",
        rejection_reason=reason,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REJECTION_REASON"


def test_decision_key_conflicts_and_terminal_different_key(adjustment_api) -> None:
    client, factory, fixture = adjustment_api
    created = _post(client, fixture.negative_recheck_id, key="terminal-create")
    adjustment_id = created.json()["adjustment_id"]
    app.dependency_overrides[get_actor] = lambda: fixture.manager
    rejected = _decide(
        client,
        adjustment_id,
        "REJECT",
        key="terminal-key",
        rejection_reason="Rejected",
    )
    assert rejected.status_code == 200
    conflicting = _decide(
        client,
        adjustment_id,
        "APPROVE",
        key="terminal-key",
    )
    assert conflicting.status_code == 409
    assert conflicting.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    different = _decide(
        client,
        adjustment_id,
        "REJECT",
        key="different-terminal-key",
        rejection_reason="Rejected",
    )
    assert different.status_code == 409
    assert different.json()["error"]["code"] == "ADJUSTMENT_NOT_PENDING"
    with factory() as session:
        assert session.scalar(select(StockBalance.quantity)) == 99


@pytest.mark.parametrize("role", [Role.WAREHOUSE_STAFF, Role.PURCHASING, Role.ADMIN])
def test_manager_adjustment_routes_forbid_wrong_roles(
    adjustment_api, role: Role
) -> None:
    client, _factory, fixture = adjustment_api
    created = _post(client, fixture.negative_recheck_id, key=f"role-create-{role}")
    adjustment_id = created.json()["adjustment_id"]
    app.dependency_overrides[get_actor] = lambda: Actor(
        uuid4(), f"wrong.{role.value.lower()}", role
    )
    assert (
        client.get("/api/v1/adjustments?status=PENDING_MANAGER_DECISION").status_code
        == 403
    )
    assert client.get(f"/api/v1/adjustments/{adjustment_id}").status_code == 403
    assert _decide(client, adjustment_id, "APPROVE").status_code == 403


def test_failure_after_applied_evidence_flush_rolls_back(
    adjustment_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, factory, fixture = adjustment_api
    created = _post(client, fixture.negative_recheck_id, key="rollback-create")
    adjustment_id = created.json()["adjustment_id"]
    with factory.begin() as session:
        balance = session.scalar(select(StockBalance))
        assert balance is not None
        balance.quantity = 10
    app.dependency_overrides[get_actor] = lambda: fixture.manager

    def fail_after_flush(*_args, **_kwargs):
        raise RuntimeError("forced post-evidence failure")

    monkeypatch.setattr(
        "warehouse_api.adjustment._log_decision_after_commit", fail_after_flush
    )
    with pytest.raises(RuntimeError, match="forced post-evidence failure"):
        _decide(client, adjustment_id, "APPROVE", key="rollback-decision")
    with factory() as session:
        request = session.get(AdjustRequest, UUID(adjustment_id))
        assert request is not None
        assert request.status == "PENDING_MANAGER_DECISION"
        assert request.decided_at is None
        assert session.scalar(select(StockBalance.quantity)) == 10
