-- Simulated send-money UI records only. This table does not represent transfers.
CREATE TABLE IF NOT EXISTS demo_transfers (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_label VARCHAR(120) NOT NULL,
    amount_paise INTEGER NOT NULL,
    note VARCHAR(240),
    status VARCHAR(24) NOT NULL DEFAULT 'SIMULATED' CHECK (status = 'SIMULATED'),
    created_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_demo_transfers_user_id ON demo_transfers(user_id);
