-- ==============================================================================
-- Migration V003: Align Payment Orders and Provider Events Schema
-- Database: SQLite & PostgreSQL compatible DDL
-- ==============================================================================

-- Ensure provider_events table exists
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

