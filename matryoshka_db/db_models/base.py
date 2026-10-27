from datetime import datetime, timezone

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def get_utc_now() -> datetime:
    """Возвращает текущее время в UTC без tzinfo для совместимости с PostgreSQL TIMESTAMP"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Соглашение об именовании ограничений для Alembic
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    metadata = metadata


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=get_utc_now, onupdate=get_utc_now)
