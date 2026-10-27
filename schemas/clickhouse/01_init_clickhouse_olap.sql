-- ClickHouse OLAP Схема: Неизменяемый журнал аудита и телеметрии суверенитета
CREATE DATABASE IF NOT EXISTS matryoshka_analytics;

CREATE TABLE IF NOT EXISTS matryoshka_analytics.audit_ledger_events (
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

-- Стохастические прогоны Монте-Карло (Supply Chain VaR)
CREATE TABLE IF NOT EXISTS matryoshka_analytics.monte_carlo_shock_runs (
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
