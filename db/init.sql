CREATE TABLE monitors (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  interval_seconds INT NOT NULL DEFAULT 60,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE checks (
  id BIGSERIAL PRIMARY KEY,
  monitor_id INT REFERENCES monitors(id) ON DELETE CASCADE,
  status_code INT,
  latency_ms INT,
  ok BOOLEAN NOT NULL,
  checked_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON checks (monitor_id, checked_at DESC);