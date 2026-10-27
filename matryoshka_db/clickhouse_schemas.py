"""Схемы, DDL и спецификации таблиц ClickHouse OLAP в архитектуре MatryoshkaAudit.

Архитектура хранения данных (Polyglot Persistence):
1. PostgreSQL 16 (OLTP):
   - Транзакционные ACID-данные: дерево изделий (BOM), пользователи, роли, поставщики,
     сертификаты соответствия ПП РФ № 719, нормативные правила отраслей.
   - Используется: enterprise-service, regulator-service.

2. ClickHouse 24 (OLAP):
   - Высоконагруженная аналитика и неизменяемый аудит:
     а) `audit_ledger_events` (ReplacingMergeTree) — неизменяемый криптографически подписанный
        журнал регуляторных аудитов, дрейфа локализации и фиксации технологического суверенитета.
     б) `monte_carlo_shock_runs` (MergeTree) — поколоночное хранение миллионов стохастических
        итераций моделирования санкционных шоков (Supply Chain VaR).
   - Точка доступа: analytics-service (единый шлюз аналитики / Analytics Gateway Pattern).
     Микросервисы взаимодействуют с ClickHouse через API analytics-service (REST/gRPC),
     сохраняя строгие границы доменов и независимость схем данных (Database-per-Service).
"""

from typing import Final

CLICKHOUSE_DATABASE_NAME: Final[str] = "matryoshka_analytics"

DDL_AUDIT_LEDGER_EVENTS: Final[str] = """
CREATE TABLE IF NOT EXISTS audit_ledger_events (
    event_id UUID,
    timestamp DateTime64(6, 'UTC'),
    trace_id LowCardinality(String),
    product_id UInt32,
    product_name LowCardinality(String),
    event_type LowCardinality(String),
    actor_type LowCardinality(String),
    paper_localization_pct Float32,
    defacto_localization_pct Float32,
    vulnerability_gap_pct Float32,
    chokepoints_count UInt16,
    digital_signature FixedString(64),
    payload_json String
) ENGINE = ReplacingMergeTree(timestamp)
ORDER BY (product_id, event_type, timestamp, event_id);
"""

DDL_MONTE_CARLO_SHOCK_RUNS: Final[str] = """
CREATE TABLE IF NOT EXISTS monte_carlo_shock_runs (
    run_id UUID,
    simulated_at DateTime64(6, 'UTC'),
    product_id UInt32,
    scenario_type LowCardinality(String),
    iteration_number UInt32,
    blocked_countries_count UInt8,
    is_halted UInt8,
    halt_days UInt16,
    value_at_risk_rub Float64,
    failed_chokepoint String
) ENGINE = MergeTree()
ORDER BY (product_id, run_id, iteration_number);
"""
