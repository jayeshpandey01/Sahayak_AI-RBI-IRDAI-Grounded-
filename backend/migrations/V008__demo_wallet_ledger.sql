-- Isolated simulated wallet funds and atomic user-to-user demo transfers.
CREATE TABLE IF NOT EXISTS demo_wallet_accounts (
    user_id VARCHAR(64) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    wallet_code VARCHAR(24) NOT NULL UNIQUE,
    balance_paise INTEGER NOT NULL DEFAULT 0 CHECK (balance_paise >= 0 AND balance_paise <= 10000000),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_demo_wallet_accounts_wallet_code
    ON demo_wallet_accounts(wallet_code);

CREATE TABLE IF NOT EXISTS demo_wallet_entries (
    id VARCHAR(64) PRIMARY KEY,
    transaction_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    counterparty_user_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    idempotency_key VARCHAR(128),
    entry_type VARCHAR(16) NOT NULL CHECK (entry_type IN ('DEMO_FUND', 'CREDIT', 'DEBIT')),
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    description VARCHAR(240) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT uq_demo_wallet_user_idempotency UNIQUE (user_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_demo_wallet_entries_transaction_id
    ON demo_wallet_entries(transaction_id);
CREATE INDEX IF NOT EXISTS ix_demo_wallet_entries_user_id
    ON demo_wallet_entries(user_id);
