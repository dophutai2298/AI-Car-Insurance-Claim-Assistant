import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Base, create_database_engine, create_session_factory
from app.services.price_catalog import seed_price_catalog


def main() -> None:
    engine = create_database_engine()
    try:
        Base.metadata.create_all(engine)
        with create_session_factory(engine)() as session:
            seed_price_catalog(session)
        print("Demo VND price catalog seeded; existing records preserved.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
