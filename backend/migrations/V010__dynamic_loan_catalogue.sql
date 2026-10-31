-- Database-backed catalogue; seed records are marked synthetic in application code.
CREATE TABLE IF NOT EXISTS loan_products (
    offer_id VARCHAR(64) PRIMARY KEY,
    lender_id VARCHAR(64) NOT NULL,
    lender_name VARCHAR(150) NOT NULL,
    product_name VARCHAR(150) NOT NULL DEFAULT 'Personal Loan',
    loan_type VARCHAR(32) NOT NULL DEFAULT 'personal',
    min_amount NUMERIC(14, 2) NOT NULL,
    max_amount NUMERIC(14, 2) NOT NULL,
    annual_interest_rate_percent NUMERIC(6, 3) NOT NULL,
    processing_fee_percent NUMERIC(6, 3) NOT NULL DEFAULT 0,
    processing_fee_gst_percent NUMERIC(6, 3) NOT NULL DEFAULT 18,
    min_tenure_months INTEGER NOT NULL,
    max_tenure_months INTEGER NOT NULL,
    min_monthly_income NUMERIC(14, 2),
    min_age INTEGER,
    max_age INTEGER,
    employment_types_json TEXT NOT NULL DEFAULT '[]',
    locations_json TEXT NOT NULL DEFAULT '[]',
    kfs_version VARCHAR(64) NOT NULL,
    kfs_effective_date VARCHAR(32) NOT NULL,
    source_name VARCHAR(150),
    source_url VARCHAR(1000),
    source_type VARCHAR(24) NOT NULL DEFAULT 'synthetic',
    last_verified_at TIMESTAMP,
    status VARCHAR(24) NOT NULL DEFAULT 'active',
    disclaimer VARCHAR(500) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_loan_products_lender_id ON loan_products(lender_id);
CREATE INDEX IF NOT EXISTS ix_loan_products_status ON loan_products(status);

CREATE TABLE IF NOT EXISTS loan_rate_history (
    id VARCHAR(64) PRIMARY KEY,
    offer_id VARCHAR(64) NOT NULL REFERENCES loan_products(offer_id) ON DELETE CASCADE,
    annual_interest_rate_percent NUMERIC(6, 3) NOT NULL,
    processing_fee_percent NUMERIC(6, 3) NOT NULL,
    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP,
    source_name VARCHAR(150),
    source_url VARCHAR(1000),
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_loan_rate_history_offer_id ON loan_rate_history(offer_id);
