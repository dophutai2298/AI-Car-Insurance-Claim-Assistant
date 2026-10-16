from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserRole


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.lower()))

    def add(self, *, email: str, full_name: str, password_hash: str, role: UserRole) -> User:
        user = User(
            email=email.lower(),
            full_name=full_name,
            password_hash=password_hash,
            role=role,
        )
        self.session.add(user)
        return user

    def list_by_role(self, role: UserRole) -> list[User]:
        return list(
            self.session.scalars(
                select(User)
                .where(User.role == role)
                .order_by(User.full_name.asc(), User.email.asc())
            )
        )
