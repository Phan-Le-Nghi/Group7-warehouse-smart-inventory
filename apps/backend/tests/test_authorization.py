from uuid import uuid4

import pytest

from warehouse_api.auth import Actor, Role, require_roles
from warehouse_api.errors import ApiError


def test_require_roles_allows_matching_role() -> None:
    actor = Actor(
        user_id=uuid4(),
        login_identifier="demo.warehouse_staff",
        role=Role.WAREHOUSE_STAFF,
    )
    dependency = require_roles(Role.WAREHOUSE_STAFF, Role.MANAGER)

    assert dependency(actor) == actor


def test_require_roles_returns_403_for_authenticated_wrong_role() -> None:
    actor = Actor(
        user_id=uuid4(),
        login_identifier="demo.purchasing",
        role=Role.PURCHASING,
    )
    dependency = require_roles(Role.WAREHOUSE_STAFF)

    with pytest.raises(ApiError) as raised:
        dependency(actor)

    assert raised.value.status_code == 403
    assert raised.value.code == "FORBIDDEN"


def test_require_roles_rejects_empty_configuration() -> None:
    with pytest.raises(ValueError):
        require_roles()
