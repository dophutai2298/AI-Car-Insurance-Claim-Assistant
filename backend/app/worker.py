import logging
import time

from app.core.config import get_settings
from app.db import create_database_engine, create_session_factory, run_database_migrations
from app.services.workflow_worker import WorkflowWorker


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if settings.database_migrate_on_startup:
        run_database_migrations(settings.database_url)
    engine = create_database_engine(settings)
    worker = WorkflowWorker(create_session_factory(engine), settings)
    try:
        while True:
            if not worker.run_once():
                time.sleep(settings.workflow_worker_poll_seconds)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
