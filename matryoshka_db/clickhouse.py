"""Shared модуль подключения к ClickHouse OLAP для пакета matryoshka_db.

Используется для прямого доступа к ClickHouse из утилит, тестов, CLI-скриптов
или сервиса аналитики (analytics-service).
"""

import logging
from typing import Any

try:
    import clickhouse_connect
    from clickhouse_connect.driver.client import Client
except ImportError:
    clickhouse_connect = None
    Client = Any

from matryoshka_db.clickhouse_schemas import (
    CLICKHOUSE_DATABASE_NAME,
    DDL_AUDIT_LEDGER_EVENTS,
    DDL_MONTE_CARLO_SHOCK_RUNS,
)

logger = logging.getLogger(__name__)


class ClickHouseConnectionManager:
    """Управление подключением к ClickHouse OLAP на уровне пакета matryoshka_db"""

    def __init__(
        self,
        host: str = "clickhouse",
        port: int = 8123,
        user: str = "default",
        password: str = "",
        database: str = CLICKHOUSE_DATABASE_NAME,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.client: Client | None = None

    def connect(self) -> Client | None:
        if not clickhouse_connect:
            logger.info("clickhouse_connect не установлен в текущем окружении")
            return None
        try:
            admin_client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
            )
            admin_client.command(f"CREATE DATABASE IF NOT EXISTS {self.database}")

            self.client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                database=self.database,
            )
            logger.info("Подключение к ClickHouse OLAP (%s:%s/%s) успешно", self.host, self.port, self.database)
            self.init_schemas()
            return self.client
        except Exception as e:  # noqa: BLE001 - resilience fallback if ClickHouse is offline
            logger.warning("ClickHouse OLAP недоступен (%s)", e)
            self.client = None
            return None

    def init_schemas(self) -> None:
        if not self.client:
            return
        self.client.command(DDL_AUDIT_LEDGER_EVENTS)
        self.client.command(DDL_MONTE_CARLO_SHOCK_RUNS)
        logger.info("Таблицы ClickHouse OLAP успешно верифицированы")

    def close(self) -> None:
        if self.client:
            try:
                self.client.close()
            except Exception:
                logger.debug("Ошибка при закрытии клиента ClickHouse", exc_info=True)


ch_manager = ClickHouseConnectionManager()
