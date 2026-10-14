"""Database construction kept explicit so tests can use isolated SQLite files."""

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def default_database_url() -> str:
    database_path = Path(__file__).resolve().parent.parent / "carenote.db"
    return f"sqlite:///{database_path}"


def build_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def build_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def session_dependency(factory: sessionmaker) -> Generator[Session, None, None]:
    with factory() as session:
        yield session

