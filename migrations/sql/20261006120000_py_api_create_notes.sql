-- An example, for docs/migrations/write-a-migration.md: py-api does not
-- call it yet. Delete it, or keep it, once py-api has a schema of its
-- own. Every name carries py-api's prefix, py_api_; the service calls
-- the accessors, not the table (docs/conduct/database.md).

-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';
CREATE TABLE IF NOT EXISTS py_api_notes (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  owner text NOT NULL,
  body text NOT NULL CHECK (length(body) <= 10000),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS py_api_notes_owner_idx ON py_api_notes (owner, id);

CREATE OR REPLACE FUNCTION py_api_note_add(p_owner text, p_body text) RETURNS bigint
  LANGUAGE sql AS $$
  INSERT INTO py_api_notes (owner, body) VALUES (p_owner, p_body) RETURNING id
$$;

CREATE OR REPLACE FUNCTION py_api_notes_of(p_owner text, p_limit int DEFAULT 50)
  RETURNS TABLE (id bigint, body text, created_at timestamptz)
  LANGUAGE sql STABLE AS $$
  SELECT n.id, n.body, n.created_at FROM py_api_notes n
  WHERE n.owner = p_owner ORDER BY n.id DESC LIMIT least(p_limit, 500)
$$;

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_notes_of(text, int);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_note_add(text, text);
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS py_api_notes;
