-- User-managed recurring bills, reminders, and manual payment history.
-- Recording a payment here does not initiate a Stripe or wallet transaction.
CREATE TABLE IF NOT EXISTS recurring_bills (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    category VARCHAR(32) NOT NULL DEFAULT 'OTHER',
    payee VARCHAR(120),
    expected_amount_paise INTEGER CHECK (expected_amount_paise IS NULL OR expected_amount_paise > 0),
    frequency VARCHAR(16) NOT NULL DEFAULT 'MONTHLY',
    next_due_date VARCHAR(10) NOT NULL,
    reminder_days_before INTEGER NOT NULL DEFAULT 3 CHECK (reminder_days_before BETWEEN 0 AND 30),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    notes VARCHAR(500),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_recurring_bills_user_id ON recurring_bills(user_id);
CREATE INDEX IF NOT EXISTS ix_recurring_bills_is_active ON recurring_bills(is_active);

CREATE TABLE IF NOT EXISTS bill_payment_records (
    id VARCHAR(64) PRIMARY KEY,
    bill_id VARCHAR(64) NOT NULL REFERENCES recurring_bills(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    due_date VARCHAR(10) NOT NULL,
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    paid_at TIMESTAMP NOT NULL,
    note VARCHAR(240),
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT uq_bill_payment_occurrence UNIQUE (bill_id, due_date)
);

CREATE INDEX IF NOT EXISTS ix_bill_payment_records_bill_id ON bill_payment_records(bill_id);
CREATE INDEX IF NOT EXISTS ix_bill_payment_records_user_id ON bill_payment_records(user_id);
