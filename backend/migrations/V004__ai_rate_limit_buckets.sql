-- Shared fixed-window counters for the free OpenRouter model. Actor identifiers are keyed hashes.
CREATE TABLE IF NOT EXISTS ai_rate_limit_buckets (
    scope VARCHAR(16) NOT NULL,
    bucket_start TIMESTAMP NOT NULL,
    actor_hash VARCHAR(64) NOT NULL DEFAULT 'global',
    request_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (scope, bucket_start, actor_hash)
);
CREATE INDEX IF NOT EXISTS idx_ai_rate_limit_bucket_start ON ai_rate_limit_buckets(bucket_start);
