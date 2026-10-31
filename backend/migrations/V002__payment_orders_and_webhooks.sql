-- ==============================================================================
-- Migration V002: Payment Orders, Provider Webhook Events, and Payment Audit Logs
-- Database: SQLite & PostgreSQL compatible DDL
-- Milestone S1 — Backend payment domain and schema
-- ==============================================================================

-- 1. Payment Orders (Core Ledger & State Machine)
CREATE TABLE IF NOT EXISTS payment_orders (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    purpose VARCHAR(64) NOT NULL,
    amount_paise INTEGER NOT NULL,
    currency VARCHAR(10) DEFAULT 'inr' NOT NULL,
    status VARCHAR(32) DEFAULT 'CREATED' NOT NULL,
    idempotency_key VARCHAR(128) UNIQUE NOT NULL,
    stripe_payment_intent_id VARCHAR(128) UNIQUE,
    stripe_client_secret VARCHAR(255),
    reference_id VARCHAR(128),
    version INTEGER DEFAULT 1 NOT NULL,
    metadata_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_payment_orders_user_id ON payment_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_orders_status ON payment_orders(status);
CREATE INDEX IF NOT EXISTS idx_payment_orders_reference_id ON payment_orders(reference_id);
CREATE INDEX IF NOT EXISTS idx_payment_orders_pi_id ON payment_orders(stripe_payment_intent_id);

-- 2. Provider Events (Webhook Ingestion & Deterministic Deduplication)
CREATE TABLE IF NOT EXISTS provider_events (
    id VARCHAR(64) PRIMARY KEY,
    provider VARCHAR(32) DEFAULT 'stripe' NOT NULL,
    event_id VARCHAR(128) UNIQUE NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    payload_json TEXT NOT NULL,
    processed BOOLEAN DEFAULT 0 NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_provider_events_event_id ON provider_events(event_id);
CREATE INDEX IF NOT EXISTS idx_provider_events_type ON provider_events(event_type);

-- 3. Payment Audit Logs (Append-Only Status Progression)
CREATE TABLE IF NOT EXISTS payment_audit_logs (
    id VARCHAR(64) PRIMARY KEY,
    order_id VARCHAR(64) NOT NULL,
    previous_status VARCHAR(32),
    new_status VARCHAR(32) NOT NULL,
    triggered_by VARCHAR(32) NOT NULL,
    reason VARCHAR(255),
    event_id VARCHAR(128),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (order_id) REFERENCES payment_orders(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_payment_audit_order_id ON payment_audit_logs(order_id);
CREATE INDEX IF NOT EXISTS idx_payment_audit_timestamp ON payment_audit_logs(timestamp);

