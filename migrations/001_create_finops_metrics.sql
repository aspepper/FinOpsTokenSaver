CREATE TABLE IF NOT EXISTS tb_finops_metrics (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(64) NOT NULL,
    request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    model_name VARCHAR(100) NOT NULL,
    prompt_tokens INT NOT NULL,
    completion_tokens INT NOT NULL,
    cache_status VARCHAR(16) NOT NULL,
    is_cache_hit BOOLEAN NOT NULL,
    estimated_cost_usd NUMERIC(12, 6) NOT NULL,
    saved_cost_usd NUMERIC(12, 6) NOT NULL,
    latency_ms INT NOT NULL,
    price_version VARCHAR(100),
    is_model_priced BOOLEAN NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_metrics_request_id ON tb_finops_metrics(request_id);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON tb_finops_metrics(request_timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_cache_hit ON tb_finops_metrics(is_cache_hit);
