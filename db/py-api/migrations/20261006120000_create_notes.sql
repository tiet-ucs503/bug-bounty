-- An example, for docs/onboarding/write-a-migration.md: py-api does not
-- use it yet. Delete it, or keep it, once py-api has a schema of its own.

-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';
CREATE TABLE IF NOT EXISTS notes (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  owner text NOT NULL,
  body text NOT NULL CHECK (length(body) <= 10000),
  created_at timestamptz NOT NULL DEFAULT now()
);

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS notes;
