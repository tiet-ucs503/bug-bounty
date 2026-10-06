---
abstract: |
  The uploads in the database: a permission in the
  users unit's matrix, and py-api's objects, the notes'
  links to them, their count, and what the collector
  may take. Two migrations, one a unit, applied and
  tried through an object's whole life, the passing of
  the grace faked in a transaction that is rolled back.
date: 2026-10-06
keywords:
- tutorial
- uploads
- db
- migration
- authz
kind: tutorial
sources:
- migrations/sql/20261006120000_py_api_create_notes.sql
status: draft
subtitle: Objects, owners, references and the grace
title: 7.2 The Database
version: v0.1.0
---

## 1 Before You Start

- [7.1 The store](1-the-store.md)
- Tutorial 3's migrations, applied

## 2 A Permission, in the Users Unit

Uploading is `objects.write`, given to members. The
matrix is the users unit's, so its new cell is a users
migration, though py-api is what asks for it: a py-api
migration may not write `users_*` tables.

``` sh
make db-new PREFIX=users NAME=grant_objects_write
```

``` sql
-- objects.write, uploading to the static bucket's objects/, for
-- members (docs/tutorials/7-uploads/2-the-database.md). The matrix is
-- the users unit's, so its cell is a users migration, though py-api
-- is what asks for it.

-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';
INSERT INTO users_grants (role, permission) VALUES ('member', 'objects.write')
ON CONFLICT DO NOTHING;

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
DELETE FROM users_grants WHERE role = 'member' AND permission = 'objects.write';
```

## 3 Objects, in py-api

``` sh
make db-new PREFIX=py_api NAME=objects
```

``` sql
-- Uploads: an object in the static bucket's objects/ for each row here,
-- (u=rw, a=r): its owner writes it, anyone reads it at static.<zone>
-- (docs/tutorials/7-uploads/2-the-database.md). A key names its owner
-- and its content, objects/<owner's tag>/<SHA-256>, so it is never
-- overwritten with other bytes, and one object has one owner. A note
-- refers to objects by its links; an object no note refers to is
-- collected once it has stood so for a while.

-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';

CREATE TABLE IF NOT EXISTS py_api_objects (
  key text PRIMARY KEY,
  owner text NOT NULL,
  sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  size bigint NOT NULL CHECK (size BETWEEN 1 AND 1048576),
  type text NOT NULL,
  -- True once the bucket holds it: the row is made first, so no object
  -- is ever in the bucket without one
  stored boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  -- When a note last let go of it; the collector's clock
  released_at timestamptz,
  UNIQUE (owner, sha256)
);

-- The references: which note refers to which object. An object a note
-- refers to cannot be deleted; a note's deletion takes its links
CREATE TABLE IF NOT EXISTS py_api_note_objects (
  note_id bigint NOT NULL REFERENCES py_api_notes (id) ON DELETE CASCADE,
  key text NOT NULL REFERENCES py_api_objects (key),
  PRIMARY KEY (note_id, key)
);
CREATE INDEX IF NOT EXISTS py_api_note_objects_key_idx ON py_api_note_objects (key);

-- Every link let go, by an edit or a note's deletion, starts its
-- object's clock: kept by a trigger, so no accessor can forget it
CREATE OR REPLACE FUNCTION py_api_note_objects_released() RETURNS trigger
  LANGUAGE plpgsql AS $$
BEGIN
  UPDATE py_api_objects SET released_at = now() WHERE key = OLD.key;
  RETURN NULL;
END
$$;
CREATE OR REPLACE TRIGGER py_api_note_objects_release AFTER DELETE ON py_api_note_objects
  FOR EACH ROW EXECUTE FUNCTION py_api_note_objects_released();

-- A new upload, the caller its owner: objects.write. Its key, and
-- whether the bucket holds it already; the same bytes twice are one
-- object, its clock started again
CREATE OR REPLACE FUNCTION py_api_object_add(p_caller text, p_sha256 text, p_size bigint, p_type text)
  RETURNS TABLE (key text, stored boolean)
  LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE
  v_key text := 'objects/' || left(encode(sha256(convert_to(p_caller, 'UTF8')), 'hex'), 16) || '/' || p_sha256;
BEGIN
  IF NOT users_may(p_caller, 'objects.write') THEN
    RAISE EXCEPTION 'objects.write needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN QUERY
    INSERT INTO py_api_objects AS o (key, owner, sha256, size, type) VALUES (v_key, p_caller, p_sha256, p_size, p_type)
    ON CONFLICT (key) DO UPDATE SET released_at = now()
    RETURNING o.key, o.stored;
END
$$;

-- The bucket holds it now
CREATE OR REPLACE FUNCTION py_api_object_stored(p_caller text, p_key text) RETURNS void
  LANGUAGE sql AS $$
  UPDATE py_api_objects SET stored = true WHERE key = p_key AND owner = p_caller
$$;

-- The caller's objects, each with its count of references: counted from
-- the links, never kept, so it cannot drift
CREATE OR REPLACE FUNCTION py_api_objects_mine(p_caller text)
  RETURNS TABLE (key text, size bigint, type text, created_at timestamptz, refs bigint)
  LANGUAGE sql STABLE AS $$
  SELECT o.key, o.size, o.type, o.created_at, (SELECT count(*) FROM py_api_note_objects l WHERE l.key = o.key)
  FROM py_api_objects o WHERE o.owner = p_caller AND o.stored ORDER BY o.created_at DESC LIMIT 500
$$;

-- The objects a note refers to, all of them at once: notes.write, the
-- note the caller's and every object the caller's own and stored. Those
-- dropped are let go, and their clocks start
CREATE OR REPLACE FUNCTION py_api_note_objects_set(p_caller text, p_note bigint, p_keys text[]) RETURNS void
  LANGUAGE plpgsql AS $$
BEGIN
  IF NOT users_may(p_caller, 'notes.write') THEN
    RAISE EXCEPTION 'notes.write needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  PERFORM 1 FROM py_api_notes WHERE id = p_note AND owner = p_caller FOR UPDATE;
  IF NOT FOUND THEN
    IF EXISTS (SELECT 1 FROM py_api_notes WHERE id = p_note) THEN
      RAISE EXCEPTION 'not your note' USING ERRCODE = 'insufficient_privilege';
    END IF;
    RAISE EXCEPTION 'no such note' USING ERRCODE = 'no_data_found';
  END IF;
  -- Held against the collector until this transaction ends
  PERFORM 1 FROM py_api_objects WHERE key = ANY (p_keys) FOR SHARE;
  IF (SELECT count(*) FROM py_api_objects WHERE key = ANY (p_keys) AND owner = p_caller AND stored)
     <> cardinality(ARRAY(SELECT DISTINCT unnest(p_keys))) THEN
    RAISE EXCEPTION 'an object that is not yours, or not stored' USING ERRCODE = 'no_data_found';
  END IF;
  DELETE FROM py_api_note_objects WHERE note_id = p_note AND NOT (key = ANY (p_keys));
  INSERT INTO py_api_note_objects (note_id, key) SELECT p_note, k FROM unnest(p_keys) k ON CONFLICT DO NOTHING;
END
$$;

-- Every note, newest first, with the objects it refers to, each its key
-- and type: notes.read.
-- Beside py_api_notes_all, whose signature is a promise
CREATE OR REPLACE FUNCTION py_api_notes_page(p_caller text, p_before bigint DEFAULT NULL, p_limit int DEFAULT 50)
  RETURNS TABLE (id bigint, body text, mine boolean, created_at timestamptz, updated_at timestamptz, objects jsonb)
  LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
BEGIN
  IF NOT users_may(p_caller, 'notes.read') THEN
    RAISE EXCEPTION 'notes.read needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN QUERY
    SELECT n.id, n.body, n.owner = p_caller, n.created_at, n.updated_at,
           coalesce((SELECT jsonb_agg(jsonb_build_object('key', l.key, 'type', o.type) ORDER BY l.key)
                     FROM py_api_note_objects l JOIN py_api_objects o ON o.key = l.key WHERE l.note_id = n.id), '[]')
    FROM py_api_notes n
    WHERE p_before IS NULL OR n.id < p_before ORDER BY n.id DESC LIMIT least(p_limit, 200);
END
$$;

-- The collector's side, no caller: up to p_limit objects no note refers
-- to, unchanged for p_grace, locked until the transaction ends, so a
-- note cannot take one up meanwhile. Call it, delete each from the
-- bucket, then forget those deleted, in one transaction
CREATE OR REPLACE FUNCTION py_api_objects_to_collect(p_grace interval, p_limit int) RETURNS SETOF text
  LANGUAGE sql AS $$
  SELECT o.key FROM py_api_objects o
  WHERE NOT EXISTS (SELECT 1 FROM py_api_note_objects l WHERE l.key = o.key)
    AND greatest(o.created_at, o.released_at) < now() - p_grace
  ORDER BY o.created_at LIMIT p_limit
  FOR UPDATE SKIP LOCKED
$$;

CREATE OR REPLACE FUNCTION py_api_objects_forget(p_keys text[]) RETURNS bigint
  LANGUAGE sql AS $$
  WITH gone AS (
    DELETE FROM py_api_objects o WHERE o.key = ANY (p_keys)
      AND NOT EXISTS (SELECT 1 FROM py_api_note_objects l WHERE l.key = o.key)
    RETURNING 1)
  SELECT count(*) FROM gone
$$;

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_objects_forget(text[]);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_objects_to_collect(interval, int);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_notes_page(text, bigint, int);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_note_objects_set(text, bigint, text[]);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_objects_mine(text);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_object_stored(text, text);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_object_add(text, text, bigint, text);
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS py_api_note_objects;
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_note_objects_released();
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS py_api_objects;
```

What it holds:

- **`py_api_objects`:** an object a row, by key, with
  its owner, size and type. `stored` turns true once
  the bucket holds it: the row is written **first**, so
  no object is ever in the bucket without one, and the
  collector can find whatever was left half done.
  `UNIQUE (owner, sha256)`: one owner's same bytes are
  one object
- **`py_api_note_objects`:** the references. A note's
  deletion takes its links (`ON DELETE CASCADE`); an
  object that a note refers to cannot be deleted, since
  its foreign key has no cascade
- **The trigger:** every link let go, by an edit or by
  a note's deletion, starts its object's clock. A
  trigger, so no accessor, present or future, can
  forget it
- **`py_api_object_add`:** `objects.write`; the key
  made here, from the owner and the hash, so no caller
  chooses it. The same bytes twice restart the clock
  and answer whether the bucket holds them already
- **`py_api_objects_mine`:** the caller's objects, each
  with `refs`, **counted from the links**
- **`py_api_note_objects_set`:** a note's whole list at
  once, `notes.write`, the note and every object the
  caller's own and stored. It locks the objects
  `FOR SHARE`, so the collector cannot take one between
  the check and the link
- **`py_api_notes_page`:** every note with its objects'
  keys and types, beside `py_api_notes_all`, whose
  signature is a promise
- **`py_api_objects_to_collect` and
  `py_api_objects_forget`:** the collector's two
  halves, no caller. The first locks what it returns,
  `FOR UPDATE SKIP LOCKED`, until its transaction ends;
  the second deletes only what still has no link

## 4 Lint, and Apply

Expect `Found 0 issues`, then `Applied:` twice:

``` sh
make db-lint
make db CMD=up
```

On the native stack,
`dbmate --url "${MIGRATOR_URL}" -d migrations/sql --no-dump-schema up`
for the second.

## 5 Try an Object's Life

Save as `try-7.sql`:

``` sql
-- Alice a member, with an upload: its row first, then, once the
-- bucket holds it, marked stored
SELECT users_admit('alice', 'alice@example.org', true);
INSERT INTO users_members (sub, role) VALUES ('alice', 'member') ON CONFLICT DO NOTHING;
SELECT key AS object, stored FROM py_api_object_add('alice', repeat('a', 64), 10, 'image/png') \gset
SELECT :'object' AS object, :'stored' AS stored;
SELECT py_api_object_stored('alice', :'object');

-- A note refers to it: one reference, counted
SELECT py_api_note_new('alice', 'with an object') AS note \gset
SELECT py_api_note_objects_set('alice', :note, ARRAY[:'object']);
SELECT refs FROM py_api_objects_mine('alice') WHERE key = :'object';

-- Bob may not take it up into a note of his
SELECT users_admit('bob', 'bob@example.org', true);
INSERT INTO users_members (sub, role) VALUES ('bob', 'member') ON CONFLICT DO NOTHING;
SELECT py_api_note_new('bob', 'bob''s') AS bobs \gset
DO $$ BEGIN
  PERFORM py_api_note_objects_set('bob', (SELECT max(id) FROM py_api_notes WHERE owner = 'bob'),
                                  ARRAY(SELECT key FROM py_api_objects WHERE owner = 'alice'));
EXCEPTION WHEN no_data_found THEN RAISE NOTICE 'bob takes alice''s object: %', SQLERRM;
END $$;

-- The note deleted: its link goes, the object is let go, and the
-- collector waits out the grace
SELECT py_api_note_drop('alice', :note);
SELECT refs FROM py_api_objects_mine('alice') WHERE key = :'object';
SELECT count(*) AS to_collect_now FROM py_api_objects_to_collect('6 hours', 10);
UPDATE py_api_objects SET created_at = created_at - interval '7 hours', released_at = released_at - interval '7 hours'
  WHERE key = :'object';
SELECT k AS to_collect_seven_hours_on FROM py_api_objects_to_collect('6 hours', 10) AS k;
SELECT py_api_objects_forget(ARRAY[:'object']) AS forgotten;
```

Run it, rolled back:

``` sh
psql "${MIGRATOR_URL}" -q -v ON_ERROR_STOP=1 -c BEGIN -f try-7.sql -c ROLLBACK
```

Expect, in order:

- alice in; her object's key,
  `objects/<16 hex>/aaa...`, and `stored` `f`;
- one reference, once her note refers to it;
- a notice: bob may not take it up,
  `an object that is not yours, or not stored`;
- after the note's deletion, `refs` `0`, and nothing to
  collect: the grace has six hours to run;
- seven hours later, as the `UPDATE` pretends, the key
  to collect; and `forgotten` `1`.

The collector deletes from the bucket between those
last two steps: tutorial 7.3.

## 6 Prove the Down, and Write the Schema

As tutorial 3's §9 and §10: `rollback` twice, `up`, and
`make db CMD=dump`.

## 7 What Can Go Wrong

- **`objects.write needed` for a member.** The users
  migration of §2 has not run, or ran after you looked:
  `SELECT * FROM users_grants WHERE role = 'member'`
- **Rolling back §3 on a stack with uploads.** The rows
  go; the objects stay in the store, and nothing will
  ever collect them. On your machine, clear the store:
  the dev stack's `store` volume, or the native stack's
  `dev/out/native/store/`. Never anywhere else
- **`an object that is not yours, or not stored`, for
  your own upload.** The bucket never confirmed it:
  `stored` is `f`. Upload it again

## 8 See Also

- [7.3 The service](3-the-service.md): next
- [3 Make it a migration](../3-the-migration.md)
