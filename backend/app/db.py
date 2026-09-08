from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


def create_database_engine(settings: Settings | None = None) -> Engine:
    current_settings = settings or get_settings()
    connect_args = {"check_same_thread": False} if current_settings.database_url.startswith("sqlite") else {}
    return create_engine(current_settings.database_url, connect_args=connect_args, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def ping_database(engine: Engine) -> bool:
    with engine.connect() as connection:
        return connection.scalar(select(1)) == 1
