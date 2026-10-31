-- Paytm provider metadata and a minimal append-only top-up credit ledger.
ALTER TABLE payment_orders ADD COLUMN provider VARCHAR(32) NOT NULL DEFAULT 'stripe';
ALTER TABLE payment_orders ADD COLUMN provider_transaction_id VARCHAR(128);
CREATE INDEX IF NOT EXISTS idx_payment_orders_provider ON payment_orders(provider);
CREATE INDEX IF NOT EXISTS idx_payment_orders_provider_txn ON payment_orders(provider_transaction_id);

CREATE TABLE IF NOT EXISTS wallet_ledger_entries (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    payment_order_id VARCHAR(64) NOT NULL UNIQUE,
    amount_paise INTEGER NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'inr',
    entry_type VARCHAR(24) NOT NULL DEFAULT 'CREDIT',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (payment_order_id) REFERENCES payment_orders(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_wallet_ledger_user ON wallet_ledger_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_wallet_ledger_order ON wallet_ledger_entries(payment_order_id);

CREATE TABLE IF NOT EXISTS payment_ai_consent_audits (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    scope VARCHAR(64) NOT NULL DEFAULT 'ai_payment_context_processing',
    is_granted BOOLEAN NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_payment_ai_consent_user ON payment_ai_consent_audits(user_id, scope, created_at);
