from dataclasses import dataclass
from os import getenv

from sqlalchemy import select
from sqlalchemy.orm import Session

from warehouse_api.auth import Role
from warehouse_api.auth_service import hash_password, verify_password
from warehouse_api.db import session_scope
from warehouse_api.models import User

DEMO_USERS = (
    ("demo.warehouse_staff", Role.WAREHOUSE_STAFF),
    ("demo.manager", Role.MANAGER),
    ("demo.purchasing", Role.PURCHASING),
    ("demo.admin", Role.ADMIN),
)


@dataclass(frozen=True, slots=True)
class SeedResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0


def seed_demo_users(session: Session, password: str) -> SeedResult:
    created = 0
    updated = 0
    unchanged = 0
    for login_identifier, role in DEMO_USERS:
        user = session.scalar(
            select(User).where(User.login_identifier == login_identifier)
        )
        if user is None:
            session.add(
                User(
                    login_identifier=login_identifier,
                    password_hash=hash_password(password),
                    role=role.value,
                    is_active=True,
                )
            )
            created += 1
            continue

        changed = False
        if user.role != role.value:
            user.role = role.value
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if not verify_password(password, user.password_hash):
            user.password_hash = hash_password(password)
            changed = True
        if changed:
            updated += 1
        else:
            unchanged += 1
    session.flush()
    return SeedResult(created=created, updated=updated, unchanged=unchanged)


def main() -> None:
    password = getenv("DEMO_USER_PASSWORD")
    if not password:
        raise RuntimeError("DEMO_USER_PASSWORD is required")
    with session_scope() as session:
        result = seed_demo_users(session, password)
    print(
        "Demo users ready: "
        f"created={result.created}, updated={result.updated}, "
        f"unchanged={result.unchanged}"
    )


if __name__ == "__main__":
    main()
