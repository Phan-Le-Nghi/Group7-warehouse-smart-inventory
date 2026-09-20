from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session

from warehouse_api.models import AuthSession, User

SESSION_LIFETIME = timedelta(hours=8)
SESSION_RETENTION = timedelta(days=7)

password_hasher = PasswordHash.recommended()
_dummy_password_hash = password_hasher.hash(token_urlsafe(32))


@dataclass(frozen=True, slots=True)
class CreatedSession:
    token: str
    expires_at: datetime


def normalize_login_identifier(login_identifier: str) -> str:
    return login_identifier.strip().lower()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password, password_hash)
    except UnknownHashError:
        return False


def authenticate_user(
    session: Session, login_identifier: str, password: str
) -> User | None:
    normalized_identifier = normalize_login_identifier(login_identifier)
    user = session.scalar(
        select(User).where(User.login_identifier == normalized_identifier)
    )
    stored_hash = user.password_hash if user is not None else _dummy_password_hash
    try:
        is_valid, updated_hash = password_hasher.verify_and_update(
            password, stored_hash
        )
    except UnknownHashError:
        is_valid, updated_hash = False, None

    if user is None or not is_valid or not user.is_active:
        return None
    if updated_hash is not None:
        user.password_hash = updated_hash
    return user


def hash_session_token(token: str) -> bytes:
    return sha256(token.encode("utf-8")).digest()


def create_session(
    session: Session, user: User, now: datetime | None = None
) -> CreatedSession:
    created_at = now or datetime.now(UTC)
    expires_at = created_at + SESSION_LIFETIME
    token = token_urlsafe(32)
    session.add(
        AuthSession(
            session_token_hash=hash_session_token(token),
            user_id=user.id,
            created_at=created_at,
            expires_at=expires_at,
        )
    )
    session.flush()
    return CreatedSession(token=token, expires_at=expires_at)


def resolve_session(
    session: Session, token: str, now: datetime | None = None
) -> tuple[AuthSession, User] | None:
    checked_at = now or datetime.now(UTC)
    row = session.execute(
        select(AuthSession, User)
        .join(User, User.id == AuthSession.user_id)
        .where(
            AuthSession.session_token_hash == hash_session_token(token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > checked_at,
            User.is_active.is_(True),
        )
    ).one_or_none()
    if row is None:
        return None
    return row._tuple()


def revoke_session(
    session: Session, auth_session: AuthSession, now: datetime | None = None
) -> None:
    if auth_session.revoked_at is None:
        auth_session.revoked_at = now or datetime.now(UTC)
        session.flush()


def cleanup_stale_sessions(session: Session, now: datetime | None = None) -> int:
    cutoff = (now or datetime.now(UTC)) - SESSION_RETENTION
    result = session.execute(
        delete(AuthSession).where(
            or_(
                AuthSession.expires_at < cutoff,
                and_(
                    AuthSession.revoked_at.is_not(None),
                    AuthSession.revoked_at < cutoff,
                ),
            )
        )
    )
    return result.rowcount or 0


def main() -> None:
    from warehouse_api.db import session_scope

    with session_scope() as session:
        deleted_count = cleanup_stale_sessions(session)
    print(f"Removed {deleted_count} expired or revoked auth sessions.")


if __name__ == "__main__":
    main()
