-- Multi-platform user loans and EMI audit records.
CREATE TABLE IF NOT EXISTS user_loans (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lender_name VARCHAR(128) NOT NULL,
    lender_type VARCHAR(32) NOT NULL DEFAULT 'BANK' CHECK (lender_type IN ('BANK', 'NBFC', 'FINTECH')),
    loan_type VARCHAR(32) NOT NULL DEFAULT 'PERSONAL' CHECK (loan_type IN ('PERSONAL', 'HOME', 'AUTO', 'EDUCATION', 'CONSUMER_DURABLE', 'CREDIT_LINE', 'GOLD')),
    account_number VARCHAR(64) NOT NULL,
    original_principal NUMERIC(14, 2) NOT NULL CHECK (original_principal > 0),
    outstanding_principal NUMERIC(14, 2) NOT NULL CHECK (outstanding_principal >= 0),
    interest_rate_percent NUMERIC(6, 2) NOT NULL CHECK (interest_rate_percent >= 0),
    tenure_months INTEGER NOT NULL CHECK (tenure_months > 0),
    remaining_tenure_months INTEGER NOT NULL CHECK (remaining_tenure_months >= 0),
    emi_amount NUMERIC(12, 2) NOT NULL CHECK (emi_amount >= 0),
    emi_due_day INTEGER NOT NULL DEFAULT 5 CHECK (emi_due_day >= 1 AND emi_due_day <= 31),
    next_due_date VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'OVERDUE', 'CLOSED', 'RESTRUCTURED')),
    disbursement_date VARCHAR(32),
    processing_fee_paid NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    prepayment_penalty_percent NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    notes TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_user_loans_user_id ON user_loans(user_id);
CREATE INDEX IF NOT EXISTS ix_user_loans_status ON user_loans(status);
CREATE INDEX IF NOT EXISTS ix_user_loans_lender_name ON user_loans(lender_name);

