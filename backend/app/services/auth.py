from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import User, UserRole
from app.repositories.users import UserRepository
from app.schemas.auth import UserCreateRequest

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("not-a-real-user-password")


class AuthService:
    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.users.find_by_email(email.strip().lower())
        stored_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
        password_matches = password_hash.verify(password, stored_hash)
        if not user or not user.is_active or not password_matches:
            return None
        return user

    def create_user(self, request: UserCreateRequest) -> User | None:
        email = request.email.strip().lower()
        if self.users.find_by_email(email) is not None:
            return None

        user = self.users.add(
            email=email,
            full_name=request.full_name or email,
            password_hash=password_hash.hash(request.password),
            role=request.role,
        )
        self.session.commit()
        self.session.refresh(user)
        return user

    def create_access_token(self, user: User) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self.settings.jwt_access_token_minutes
        )
        return jwt.encode(
            {"sub": user.email, "role": user.role.value, "exp": expires_at},
            self.settings.jwt_secret,
            algorithm=ALGORITHM,
        )

    def user_from_token(self, token: str) -> User | None:
        try:
            payload = jwt.decode(token, self.settings.jwt_secret, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if not isinstance(email, str):
                return None
        except InvalidTokenError:
            return None

        user = self.users.find_by_email(email)
        return user if user and user.is_active else None


def seed_demo_users(session: Session, settings: Settings) -> None:
    users = UserRepository(session)
    demo_users = (
        (settings.admin_email, "Demo Admin", settings.admin_password, UserRole.ADMIN),
        (settings.adjuster_email, "Demo Adjuster", settings.adjuster_password, UserRole.ADJUSTER),
    )

    for email, full_name, plain_password, role in demo_users:
        if users.find_by_email(email) is None:
            users.add(
                email=email,
                full_name=full_name,
                password_hash=password_hash.hash(plain_password),
                role=role,
            )

    session.commit()
