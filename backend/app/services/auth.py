import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet, InvalidToken as InvalidEncryptedToken
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import User, UserRole
from app.repositories.auth_sessions import AuthRateLimitRepository, RefreshSessionRepository
from app.repositories.users import UserRepository
from app.schemas.auth import UserCreateRequest, UserSecurityUpdateRequest

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("not-a-real-user-password")


class AuthRateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after


class AuthService:
    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.refresh_sessions = RefreshSessionRepository(session)
        self.rate_limits = AuthRateLimitRepository(session)

    def check_rate_limit(self, operation: str, identifier: str) -> None:
        key = hashlib.sha256(identifier.strip().lower().encode()).hexdigest()
        window = timedelta(seconds=self.settings.auth_rate_limit_window_seconds)
        for attempt in range(2):
            now = datetime.now(timezone.utc)
            record = self.rate_limits.find_for_update(operation, key)
            if record is None:
                self.rate_limits.add(operation, key, now)
            else:
                started_at = self._as_utc(record.window_started_at)
                if now - started_at >= window:
                    record.window_started_at = now
                    record.attempts = 1
                elif record.attempts >= self.settings.auth_rate_limit_attempts:
                    retry_after = max(
                        1, int((started_at + window - now).total_seconds())
                    )
                    self.session.rollback()
                    raise AuthRateLimitExceeded(retry_after)
                else:
                    record.attempts += 1
            try:
                self.session.commit()
                return
            except IntegrityError:
                self.session.rollback()
                if attempt:
                    raise

    def clear_rate_limit(self, operation: str, identifier: str) -> None:
        key = hashlib.sha256(identifier.strip().lower().encode()).hexdigest()
        self.rate_limits.clear(operation, key)
        self.session.commit()

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

    def update_user_security(
        self, email: str, request: UserSecurityUpdateRequest
    ) -> User | None:
        user = self.users.find_by_email(email.strip().lower())
        if user is None:
            return None
        changed = False
        if request.password is not None:
            user.password_hash = password_hash.hash(request.password)
            changed = True
        if request.is_active is not None and request.is_active != user.is_active:
            user.is_active = request.is_active
            changed = True
        if changed:
            user.auth_version += 1
            self.refresh_sessions.revoke_user(user.id)
            self.session.commit()
            self.session.refresh(user)
        return user

    def create_access_token(self, user: User) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self.settings.jwt_access_token_minutes
        )
        return jwt.encode(
            {
                "sub": user.email,
                "role": user.role.value,
                "ver": user.auth_version,
                "typ": "access",
                "exp": expires_at,
            },
            self.settings.jwt_secret,
            algorithm=ALGORITHM,
        )

    def issue_session(self, user: User, family_id: str | None = None) -> tuple[str, str]:
        raw_refresh = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        self.refresh_sessions.add(
            user_id=user.id,
            family_id=family_id or secrets.token_hex(16),
            token_hash=self._token_hash(raw_refresh),
            expires_at=now + timedelta(days=self.settings.jwt_refresh_token_days),
        )
        self.session.commit()
        return self.create_access_token(user), raw_refresh

    def rotate_refresh_token(self, raw_refresh: str) -> tuple[User, str, str] | None:
        record = self.refresh_sessions.find_for_update(self._token_hash(raw_refresh))
        if record is None:
            return None
        now = datetime.now(timezone.utc)
        if (
            record.revoked_at is not None
            or record.rotated_at is not None
            or self._as_utc(record.expires_at) <= now
        ):
            self.refresh_sessions.revoke_family(record.family_id)
            self.session.commit()
            return None
        user = self.users.find_by_id(record.user_id)
        if user is None or not user.is_active:
            self.refresh_sessions.revoke_family(record.family_id)
            self.session.commit()
            return None
        record.rotated_at = now
        access_token, new_refresh = self.issue_session(user, record.family_id)
        return user, access_token, new_refresh

    def logout(self, raw_refresh: str) -> None:
        record = self.refresh_sessions.find_for_update(self._token_hash(raw_refresh))
        if record is not None:
            self.refresh_sessions.revoke_family(record.family_id)
            self.session.commit()

    def user_from_token(self, token: str) -> User | None:
        payload = self._decode_token(token, "access")
        if payload is None:
            return None
        email = payload.get("sub")
        version = payload.get("ver")
        if not isinstance(email, str) or not isinstance(version, int):
            return None
        user = self.users.find_by_email(email)
        return user if user and user.is_active and user.auth_version == version else None

    def create_mfa_challenge_token(self, user: User) -> str:
        return jwt.encode(
            {
                "sub": user.email,
                "ver": user.auth_version,
                "typ": "mfa",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            self.settings.jwt_secret,
            algorithm=ALGORITHM,
        )

    def enroll_mfa(self, user: User, secret: str, code: str) -> list[str] | None:
        normalized_secret = secret.replace(" ", "").upper()
        if not self._verify_totp(normalized_secret, code):
            return None
        recovery_codes = [secrets.token_hex(5).upper() for _ in range(8)]
        user.mfa_secret_encrypted = self._fernet().encrypt(normalized_secret.encode()).decode()
        user.mfa_recovery_codes_json = json.dumps(
            [self._token_hash(item) for item in recovery_codes]
        )
        user.mfa_enabled = True
        user.auth_version += 1
        self.refresh_sessions.revoke_user(user.id)
        self.session.commit()
        return recovery_codes

    def complete_mfa_challenge(
        self,
        challenge_token: str,
        *,
        code: str | None,
        recovery_code: str | None,
    ) -> tuple[User, str, str] | None:
        payload = self._decode_token(challenge_token, "mfa")
        if payload is None:
            return None
        user = self.users.find_by_email(str(payload.get("sub", "")))
        if (
            user is None
            or not user.is_active
            or not user.mfa_enabled
            or payload.get("ver") != user.auth_version
        ):
            return None
        valid = False
        if code:
            secret = self._decrypt_mfa_secret(user)
            valid = secret is not None and self._verify_totp(secret, code)
        elif recovery_code:
            hashes = json.loads(user.mfa_recovery_codes_json)
            candidate = self._token_hash(recovery_code.strip().upper())
            if candidate in hashes:
                hashes.remove(candidate)
                user.mfa_recovery_codes_json = json.dumps(hashes)
                valid = True
        if not valid:
            return None
        access_token, refresh_token = self.issue_session(user)
        return user, access_token, refresh_token

    def _decode_token(self, token: str, expected_type: str) -> dict[str, object] | None:
        try:
            payload = jwt.decode(token, self.settings.jwt_secret, algorithms=[ALGORITHM])
        except InvalidTokenError:
            return None
        return payload if payload.get("typ") == expected_type else None

    def _fernet(self) -> Fernet:
        key = base64.urlsafe_b64encode(hashlib.sha256(self.settings.jwt_secret.encode()).digest())
        return Fernet(key)

    def _decrypt_mfa_secret(self, user: User) -> str | None:
        if not user.mfa_secret_encrypted:
            return None
        try:
            return self._fernet().decrypt(user.mfa_secret_encrypted.encode()).decode()
        except InvalidEncryptedToken:
            return None

    @staticmethod
    def _verify_totp(secret: str, code: str) -> bool:
        try:
            key = base64.b32decode(secret, casefold=True)
        except (ValueError, TypeError):
            return False
        counter = int(time.time()) // 30
        for drift in (-1, 0, 1):
            digest = hmac.new(key, struct.pack(">Q", counter + drift), hashlib.sha1).digest()
            offset = digest[-1] & 0x0F
            value = (
                struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
            ) % 1_000_000
            if hmac.compare_digest(f"{value:06d}", code):
                return True
        return False

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


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
