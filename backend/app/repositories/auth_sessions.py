from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AuthRateLimit, RefreshSession


class RefreshSessionRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, **values) -> RefreshSession:
        record = RefreshSession(**values)
        self.session.add(record)
        self.session.flush()
        return record

    def find_for_update(self, token_hash: str) -> RefreshSession | None:
        return self.session.scalar(
            select(RefreshSession)
            .where(RefreshSession.token_hash == token_hash)
            .with_for_update()
        )

    def revoke_family(self, family_id: str) -> None:
        now = datetime.now(timezone.utc)
        records = self.session.scalars(
            select(RefreshSession).where(
                RefreshSession.family_id == family_id,
                RefreshSession.revoked_at.is_(None),
            )
        )
        for record in records:
            record.revoked_at = now

    def revoke_user(self, user_id: int) -> None:
        now = datetime.now(timezone.utc)
        records = self.session.scalars(
            select(RefreshSession).where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
            )
        )
        for record in records:
            record.revoked_at = now


class AuthRateLimitRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_for_update(self, operation: str, identifier: str) -> AuthRateLimit | None:
        return self.session.scalar(
            select(AuthRateLimit)
            .where(
                AuthRateLimit.operation == operation,
                AuthRateLimit.identifier == identifier,
            )
            .with_for_update()
        )

    def add(self, operation: str, identifier: str, now: datetime) -> AuthRateLimit:
        record = AuthRateLimit(
            operation=operation,
            identifier=identifier,
            window_started_at=now,
            attempts=1,
        )
        self.session.add(record)
        return record

    def clear(self, operation: str, identifier: str) -> None:
        self.session.execute(
            delete(AuthRateLimit).where(
                AuthRateLimit.operation == operation,
                AuthRateLimit.identifier == identifier,
            )
        )
