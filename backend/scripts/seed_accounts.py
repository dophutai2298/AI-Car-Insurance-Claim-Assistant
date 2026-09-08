import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db import Base, create_database_engine, create_session_factory
from app.models import UserRole
from app.schemas.auth import UserCreateRequest
from app.services.auth import AuthService


@dataclass(frozen=True)
class AccountSpec:
    email: str
    full_name: str
    password: str
    role: UserRole


# Update this list before running the script to create a different account set.
ACCOUNTS: tuple[AccountSpec, ...] = (
    AccountSpec("admin1@email.com", "Admin One", "123456", UserRole.ADMIN),
    AccountSpec("admin2@email.com", "Admin Two", "123456", UserRole.ADMIN),
    AccountSpec("assistant1@email.com", "Assistant One", "123456", UserRole.ADJUSTER),
    AccountSpec("assistant2@email.com", "Assistant Two", "123456", UserRole.ADJUSTER),
)


def main() -> None:
    settings = get_settings()
    engine = create_database_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        service = AuthService(session, settings)
        for account in ACCOUNTS:
            user = service.create_user(
                UserCreateRequest(
                    email=account.email,
                    full_name=account.full_name,
                    password=account.password,
                    role=account.role,
                )
            )
            result = "created" if user else "already exists"
            print(f"{account.email} ({account.role.value}): {result}")

    engine.dispose()


if __name__ == "__main__":
    main()
