from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserRole


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.lower()))

    def find_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def first_active_adjuster(self) -> User | None:
        return self.session.scalar(
            select(User)
            .where(User.role == UserRole.ADJUSTER, User.is_active.is_(True))
            .order_by(User.id)
        )

    def emails_by_ids(self, user_ids: set[int]) -> dict[int, str]:
        if not user_ids:
            return {}
        return dict(
            self.session.execute(
                select(User.id, User.email).where(User.id.in_(user_ids))
            ).all()
        )

    def add(self, *, email: str, full_name: str, password_hash: str, role: UserRole) -> User:
        user = User(
            email=email.lower(),
            full_name=full_name,
            password_hash=password_hash,
            role=role,
        )
        self.session.add(user)
        return user
