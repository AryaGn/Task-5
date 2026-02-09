CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    yc_company_id TEXT UNIQUE,
    name TEXT,
    domain TEXT,
    founded_year INT,
    first_seen_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS company_snapshots (
    id SERIAL PRIMARY KEY,
    company_id INT REFERENCES companies(id),
    batch TEXT,
    stage TEXT,
    description TEXT,
    location TEXT,
    tags JSONB,
    employee_range TEXT,
    scraped_at TIMESTAMP,
    snapshot_hash TEXT
);
CREATE TABLE IF NOT EXISTS company_changes (
    id SERIAL PRIMARY KEY,
    company_id INT REFERENCES companies(id),
    change_type TEXT,
    old_value TEXT,
    new_value TEXT,
    detected_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS company_scores (
    company_id INT PRIMARY KEY REFERENCES companies(id),
    momentum_score NUMERIC,
    stability_score NUMERIC,
    last_computed_at TIMESTAMP
);
ALTER TABLE companies
ADD COLUMN IF NOT EXISTS search_vector tsvector;

CREATE INDEX IF NOT EXISTS idx_companies_search
ON companies
USING GIN(search_vector);
CREATE OR REPLACE FUNCTION update_company_search_vector()
RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    to_tsvector(
      'english',
      COALESCE(NEW.name, '')
    );
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_search_vector ON companies;

CREATE TRIGGER trg_update_search_vector
BEFORE INSERT OR UPDATE
ON companies
FOR EACH ROW
EXECUTE FUNCTION update_company_search_vector();
