import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import create_database_engine, ping_database


def main() -> None:
    engine = create_database_engine()
    assert ping_database(engine)


if __name__ == "__main__":
    main()
