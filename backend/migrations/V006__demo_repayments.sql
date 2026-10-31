-- Synthetic-only repayment events for the clearly labeled demo behavior indicator.
-- These rows must never be treated as lender-confirmed payments or bureau data.
CREATE TABLE IF NOT EXISTS demo_repayments (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    journey_id VARCHAR(64) NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    due_at TIMESTAMP NOT NULL,
    amount_paise INTEGER NOT NULL,
    status VARCHAR(24) NOT NULL CHECK (status IN ('PAID_ON_TIME', 'PAID_LATE', 'MISSED', 'UPCOMING')),
    recorded_at TIMESTAMP NOT NULL,
    source VARCHAR(24) NOT NULL DEFAULT 'simulation' CHECK (source = 'simulation')
);
CREATE INDEX IF NOT EXISTS ix_demo_repayments_user_id ON demo_repayments(user_id);
CREATE INDEX IF NOT EXISTS ix_demo_repayments_journey_id ON demo_repayments(journey_id);
