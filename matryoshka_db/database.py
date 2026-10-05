import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер асинхронных соединений с PostgreSQL (SQLAlchemy 2.0 + asyncpg)"""

    def __init__(self, database_url: str | None = None):
        self.database_url = (
            database_url
            or os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://matryoshka:matryoshka_pass@localhost:5432/matryoshka_db",
            )
        )

        self.engine: AsyncEngine = create_async_engine(
            self.database_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            future=True,
        )

        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info("Менеджер базы данных MatryoshkaAudit инициализирован")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self):
        await self.engine.dispose()
        logger.info("Пул соединений с БД закрыт")


db_manager = DatabaseManager()
