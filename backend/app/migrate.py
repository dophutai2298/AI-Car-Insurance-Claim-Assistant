from app.core.config import get_settings
from app.db import run_database_migrations


def main() -> None:
    run_database_migrations(get_settings().database_url)


if __name__ == "__main__":
    main()
