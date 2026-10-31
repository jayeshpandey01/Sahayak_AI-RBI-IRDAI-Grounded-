-- ==============================================================================
-- Migration V001: Initial Core Relational Schema
-- Database: SQLite & PostgreSQL compatible DDL
-- ==============================================================================

-- 1. Users table (Identity & RBAC)
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(150),
    auth_provider VARCHAR(32) DEFAULT 'email',
    google_sub VARCHAR(128),
    role VARCHAR(32) DEFAULT 'borrower',
    is_active BOOLEAN DEFAULT 1,
    is_verified BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- 2. Password Reset Tokens
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    otp_code VARCHAR(16) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Loan Journeys table (FSM state machine)
CREATE TABLE IF NOT EXISTS journeys (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) DEFAULT 'user_sahayak_demo',
    stage VARCHAR(64) NOT NULL,
    language VARCHAR(16) NOT NULL,
    loan_amount NUMERIC(12, 2) NOT NULL,
    preferred_tenure_months INTEGER NOT NULL,
    maximum_emi NUMERIC(12, 2),
    purpose VARCHAR(255) NOT NULL,
    selected_offer_id VARCHAR(64),
    customer_confirmed BOOLEAN DEFAULT 0,
    ready_for_handoff BOOLEAN DEFAULT 0,
    human_review_required BOOLEAN DEFAULT 0,
    human_review_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Document Ingestion Records
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id VARCHAR(64) UNIQUE NOT NULL,
    journey_id VARCHAR(64) NOT NULL,
    document_type VARCHAR(64) NOT NULL,
    quality_score REAL NOT NULL,
    fields_json TEXT NOT NULL,
    is_confirmed BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (journey_id) REFERENCES journeys(id) ON DELETE CASCADE
);

-- 5. Consent & Statutory Audit Trail
CREATE TABLE IF NOT EXISTS consent_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consent_id VARCHAR(64) UNIQUE NOT NULL,
    journey_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) DEFAULT 'user_sahayak_demo',
    scope VARCHAR(64) NOT NULL,
    purpose TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(64),
    user_agent TEXT,
    is_granted BOOLEAN NOT NULL,
    tamper_hash VARCHAR(64) NOT NULL,
    FOREIGN KEY (journey_id) REFERENCES journeys(id) ON DELETE CASCADE
);

-- 6. Idempotency Records
CREATE TABLE IF NOT EXISTS idempotency_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotency_key VARCHAR(128) UNIQUE NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    response_status INTEGER NOT NULL,
    response_body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

