---
abstract: |
  Step 4 of tutorial 3: what makes the eight tests
  pass. The prefix given, three migrations made from
  the drafts, each with its undoing, the lint, and the
  schema written down.
date: 2026-10-07
keywords:
- tutorial
- db
- migration
- dbmate
kind: tutorial
sources:
- migrations/sql/20261006120000_py_api_begin.sql
- box/render.py
- Makefile
status: draft
subtitle: Step 4, the code
title: "3.4 Make It a Migration: the Implementation"
version: v0.1.0
---

## 1 Before You Start

- [The contract](2-contract.md): every file and
  function below is one of its entries
- [The tests](3-tests.md), saved as `test-3.sh`, run
  once and failing

Make the three migrations in this order: `make db-new`
stamps each with the time, and the time is the order.
Run the tests after any step, if you like: the count of
passes only grows.

## 2 Give the Unit Its Prefix

In `box/project.json`, py-api's `"prefix": "py_api"`
becomes, its own first (R1, T3.1):

``` json
"prefixes": ["py_api", "users"],
```

For JavaScript, js-api's
`"prefixes": ["js_api", "users"]`. Expect the two
services as before, agreeing with `services/`:

``` sh
make check
```

## 3 The People

Make the file. Expect its path,
`migrations/sql/<version>_users_create_people.sql`:

``` sh
make db-new PREFIX=users NAME=create_people
```

Under `-- migrate:up`, after the two `SET` lines, the
whole of tutorial 1's part of `users-draft.sql`, as it
is. Under `-- migrate:down`, its undoing: the
functions, then the tables, each in the reverse of the
order it was made, since a table cannot go before one
that refers to it. A `squawk-ignore` line above each
drop tells the linter the drop is meant. The file,
whole:

``` sql
-- The users unit's people: who signed in, as the sign-in says, and the
-- profile the project keeps of each (docs/tutorials/1-authentication.md).
-- Every name carries the prefix users_.

-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';

-- The people who have signed in, one row each, by Cognito's sub: what
-- the sign-in says of them. Rewritten at every sign-in, since Cognito
-- is its source of truth
CREATE TABLE IF NOT EXISTS users_people (
  sub text PRIMARY KEY,
  email text NOT NULL CHECK (email = lower(email)),
  provider text NOT NULL,
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  seen_at timestamptz NOT NULL DEFAULT now()
);

-- What the project keeps of each person beyond the sign-in. Its columns
-- are the project's to choose; a sign-in never writes them
CREATE TABLE IF NOT EXISTS users_profiles (
  sub text PRIMARY KEY REFERENCES users_people (sub) ON DELETE CASCADE,
  display_name text NOT NULL DEFAULT '' CHECK (length(display_name) <= 80),
  affiliation text NOT NULL DEFAULT '' CHECK (length(affiliation) <= 120),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- At every sign-in: a person whose e-mail is verified is recorded, or
-- their record brought up to date, and given an empty profile the first
-- time. True if recorded; anyone else is not kept
CREATE OR REPLACE FUNCTION users_person_see(p_sub text, p_email text, p_verified boolean, p_provider text)
  RETURNS boolean LANGUAGE plpgsql AS $$
BEGIN
  IF NOT coalesce(p_verified, false) OR coalesce(p_email, '') = '' THEN
    RETURN false;
  END IF;
  INSERT INTO users_people (sub, email, provider) VALUES (p_sub, lower(p_email), p_provider)
    ON CONFLICT (sub) DO UPDATE SET email = EXCLUDED.email, provider = EXCLUDED.provider, seen_at = now();
  INSERT INTO users_profiles (sub) VALUES (p_sub) ON CONFLICT DO NOTHING;
  RETURN true;
END
$$;

-- A person's record and profile together; no row if never recorded
CREATE OR REPLACE FUNCTION users_profile_get(p_sub text)
  RETURNS TABLE (sub text, email text, provider text, display_name text, affiliation text)
  LANGUAGE sql STABLE AS $$
  SELECT p.sub, p.email, p.provider, f.display_name, f.affiliation
  FROM users_people p JOIN users_profiles f ON f.sub = p.sub WHERE p.sub = p_sub
$$;

-- A person's own profile, changed. The service passes the caller's own
-- sub; who may change another's is tutorial 2's
CREATE OR REPLACE FUNCTION users_profile_set(p_sub text, p_display_name text, p_affiliation text) RETURNS void
  LANGUAGE plpgsql AS $$
BEGIN
  UPDATE users_profiles SET display_name = p_display_name, affiliation = p_affiliation, updated_at = now()
    WHERE sub = p_sub;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'no such person' USING ERRCODE = 'no_data_found';
  END IF;
END
$$;

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS users_profile_set(text, text, text);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS users_profile_get(text);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS users_person_see(text, text, boolean, text);
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS users_profiles;
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS users_people;
```

The draft was already written to run twice:
`IF NOT EXISTS` on every table and index, `OR REPLACE`
on every function, `ON CONFLICT DO NOTHING` on every
seed. A migration that fails part way runs again (R8).

## 4 The Roles

``` sh
make db-new PREFIX=users NAME=create_roles
```

Under `-- migrate:up`, tutorial 2's part of
`users-draft.sql`. Under `-- migrate:down`, the trigger
first, since it lives on tutorial 1's `users_people`,
which this file must leave as it found it; then the
functions, then the tables:

``` sql
-- The users unit's roles: what each person may do, an access control
-- matrix, and the role a person starts with
-- (docs/tutorials/2-authorisation/). Three functions are published for
-- other units (docs/conduct/database.md §3): users_may, for their
-- accessors; users_permission_add and users_permission_drop, for their
-- migrations.

-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';

-- The roles. A person who holds none may do nothing
CREATE TABLE IF NOT EXISTS users_roles (
  role text PRIMARY KEY CHECK (role ~ '^[a-z][a-z0-9-]{1,30}$'),
  about text NOT NULL DEFAULT ''
);

-- Who holds which role
CREATE TABLE IF NOT EXISTS users_members (
  sub text NOT NULL REFERENCES users_people (sub) ON DELETE CASCADE,
  role text NOT NULL REFERENCES users_roles (role) ON DELETE CASCADE,
  PRIMARY KEY (sub, role)
);
CREATE INDEX IF NOT EXISTS users_members_role_idx ON users_members (role);

-- The permissions there are, each brought by the unit that asks for
-- it. A permission is <unit>.<verb>: users.grant, notes.read
CREATE TABLE IF NOT EXISTS users_permissions (
  permission text PRIMARY KEY CHECK (permission ~ '^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*$'),
  about text NOT NULL DEFAULT ''
);

-- The access control matrix: one row for each cell that says yes
CREATE TABLE IF NOT EXISTS users_grants (
  role text NOT NULL REFERENCES users_roles (role) ON DELETE CASCADE,
  permission text NOT NULL REFERENCES users_permissions (permission) ON DELETE CASCADE,
  PRIMARY KEY (role, permission)
);
CREATE INDEX IF NOT EXISTS users_grants_permission_idx ON users_grants (permission);

-- Published, for every unit: may this person do this?
CREATE OR REPLACE FUNCTION users_may(p_sub text, p_permission text) RETURNS boolean
  LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM users_members m JOIN users_grants g ON g.role = m.role
    WHERE m.sub = p_sub AND g.permission = p_permission)
$$;
COMMENT ON FUNCTION users_may(text, text) IS 'published: may this person do this? Called by every unit';

-- The caller: e-mail, roles and permissions; no row if never signed in
CREATE OR REPLACE FUNCTION users_me(p_sub text)
  RETURNS TABLE (sub text, email text, roles text[], permissions text[])
  LANGUAGE sql STABLE AS $$
  SELECT p.sub, p.email,
    coalesce((SELECT array_agg(m.role ORDER BY m.role) FROM users_members m WHERE m.sub = p.sub), '{}'),
    coalesce((SELECT array_agg(DISTINCT g.permission ORDER BY g.permission)
              FROM users_members m JOIN users_grants g ON g.role = m.role WHERE m.sub = p.sub), '{}')
  FROM users_people p WHERE p.sub = p_sub
$$;

-- Everyone signed in, with their roles: users.read
CREATE OR REPLACE FUNCTION users_list(p_caller text)
  RETURNS TABLE (sub text, email text, roles text[], first_seen_at timestamptz, seen_at timestamptz)
  LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
BEGIN
  IF NOT users_may(p_caller, 'users.read') THEN
    RAISE EXCEPTION 'users.read needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN QUERY
    SELECT p.sub, p.email, coalesce(array_agg(m.role ORDER BY m.role) FILTER (WHERE m.role IS NOT NULL), '{}'),
           p.first_seen_at, p.seen_at
    FROM users_people p LEFT JOIN users_members m ON m.sub = p.sub
    GROUP BY p.sub ORDER BY p.email LIMIT 1000;
END
$$;

-- The matrix itself, role by role: users.read
CREATE OR REPLACE FUNCTION users_matrix(p_caller text)
  RETURNS TABLE (role text, about text, permissions text[])
  LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
BEGIN
  IF NOT users_may(p_caller, 'users.read') THEN
    RAISE EXCEPTION 'users.read needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN QUERY
    SELECT r.role, r.about,
           coalesce(array_agg(g.permission ORDER BY g.permission) FILTER (WHERE g.permission IS NOT NULL), '{}')
    FROM users_roles r LEFT JOIN users_grants g ON g.role = r.role
    GROUP BY r.role ORDER BY r.role;
END
$$;

-- Give a person a role: users.grant
CREATE OR REPLACE FUNCTION users_grant(p_caller text, p_sub text, p_role text) RETURNS void
  LANGUAGE plpgsql AS $$
BEGIN
  IF NOT users_may(p_caller, 'users.grant') THEN
    RAISE EXCEPTION 'users.grant needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM users_people WHERE sub = p_sub) THEN
    RAISE EXCEPTION 'no such person' USING ERRCODE = 'no_data_found';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM users_roles WHERE role = p_role) THEN
    RAISE EXCEPTION 'no such role' USING ERRCODE = 'no_data_found';
  END IF;
  INSERT INTO users_members (sub, role) VALUES (p_sub, p_role) ON CONFLICT DO NOTHING;
END
$$;

-- Take a role away: users.grant. Never the last users.grant there is,
-- so the project cannot lock itself out
CREATE OR REPLACE FUNCTION users_revoke(p_caller text, p_sub text, p_role text) RETURNS void
  LANGUAGE plpgsql AS $$
BEGIN
  IF NOT users_may(p_caller, 'users.grant') THEN
    RAISE EXCEPTION 'users.grant needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  DELETE FROM users_members WHERE sub = p_sub AND role = p_role;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'no such person with that role' USING ERRCODE = 'no_data_found';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM users_members m JOIN users_grants g ON g.role = m.role
                 WHERE g.permission = 'users.grant') THEN
    RAISE EXCEPTION 'the last users.grant: grant it to someone else first' USING ERRCODE = 'restrict_violation';
  END IF;
END
$$;

-- Starting roles: at a person's first sign-in, the first rule by
-- position whose pattern their e-mail is LIKE gives its role. Read
-- once; no match, no role
CREATE TABLE IF NOT EXISTS users_starting_roles (
  position bigint PRIMARY KEY,
  pattern text NOT NULL CHECK (pattern = lower(pattern)),
  role text NOT NULL REFERENCES users_roles (role) ON DELETE CASCADE
);

CREATE OR REPLACE FUNCTION users_person_start() RETURNS trigger
  LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO users_members (sub, role)
    SELECT NEW.sub, s.role FROM users_starting_roles s
    WHERE NEW.email LIKE s.pattern ORDER BY s.position LIMIT 1
  ON CONFLICT DO NOTHING;
  RETURN NULL;
END
$$;
CREATE OR REPLACE TRIGGER users_people_start AFTER INSERT ON users_people
  FOR EACH ROW EXECUTE FUNCTION users_person_start();

-- Published, for every unit's migration: a permission, and the roles
-- that start with it. Twice is once
CREATE OR REPLACE FUNCTION users_permission_add(p_permission text, p_about text, p_roles text[] DEFAULT '{}')
  RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM unnest(p_roles) r WHERE r NOT IN (SELECT role FROM users_roles)) THEN
    RAISE EXCEPTION 'no such role' USING ERRCODE = 'no_data_found';
  END IF;
  INSERT INTO users_permissions (permission, about) VALUES (p_permission, p_about) ON CONFLICT DO NOTHING;
  INSERT INTO users_grants (role, permission) SELECT r, p_permission FROM unnest(p_roles) r ON CONFLICT DO NOTHING;
END
$$;
COMMENT ON FUNCTION users_permission_add(text, text, text[]) IS 'published: a unit''s migration adds its permission';

-- Published, for every unit's migration, on its way down: the
-- permission and every cell of it. Never the users unit's own
CREATE OR REPLACE FUNCTION users_permission_drop(p_permission text) RETURNS void
  LANGUAGE plpgsql AS $$
BEGIN
  IF p_permission LIKE 'users.%' THEN
    RAISE EXCEPTION 'the users unit''s own permission' USING ERRCODE = 'insufficient_privilege';
  END IF;
  DELETE FROM users_permissions WHERE permission = p_permission;
END
$$;
COMMENT ON FUNCTION users_permission_drop(text) IS 'published: a unit''s migration takes its permission away';

-- The roles the project starts with, and the users unit's own
-- permissions; no starting roles
INSERT INTO users_roles (role, about) VALUES
  ('reader', 'reads what each unit lets it'),
  ('member', 'reads and writes what each unit lets it'),
  ('admin', 'reads the people and the matrix, grants and revokes roles')
ON CONFLICT DO NOTHING;

SELECT users_permission_add('users.read', 'reads the people and the matrix', '{admin}'),
       users_permission_add('users.grant', 'grants and revokes roles', '{admin}');

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
-- squawk-ignore ban-drop-trigger
DROP TRIGGER IF EXISTS users_people_start ON users_people;
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS users_person_start();
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS users_permission_drop(text);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS users_permission_add(text, text, text[]);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS users_revoke(text, text, text);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS users_grant(text, text, text);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS users_matrix(text);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS users_list(text);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS users_me(text);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS users_may(text, text);
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS users_starting_roles;
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS users_grants;
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS users_permissions;
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS users_members;
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS users_roles;
```

## 5 The First Admin

Nobody starts with a role, and only an admin gives
roles, so someone must be the first. A migration of its
own, so it is the one place an address is written (R7):

``` sh
make db-new PREFIX=users NAME=first_admin
```

And write, with **your** address for `you@example.org`:

``` sql
-- The project's first admin, by e-mail: a starting role, admin, for
-- their first sign-in, or admin now if they have signed in already.
-- Your own address: the repository holds it, so mind who can read the
-- repository (docs/tutorials/3-the-migration/4-implementation.md §5).

-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';
INSERT INTO users_starting_roles (position, pattern, role) VALUES (1, 'you@example.org', 'admin')
ON CONFLICT DO NOTHING;
INSERT INTO users_members (sub, role)
  SELECT p.sub, 'admin' FROM users_people p WHERE p.email = 'you@example.org'
ON CONFLICT DO NOTHING;

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
DELETE FROM users_starting_roles WHERE position = 1 AND pattern = 'you@example.org';
```

A starting role at position 1, before every other: at
your first sign-in, you start as `admin`. If you have
signed in already, the second statement makes you one
now.

> [!WARNING]
> The address is in the repository for good, and in its
> history. If the repository is public, so is it. An
> address made for the role keeps your own out of it.

Then run the tests with your address:
`FIRST_ADMIN=<your address> ./test-3.sh`.

## 6 Lint, and Apply

Squawk reads every migration for what could lock or
lose data on a live database. Expect `Found 0 issues`:

``` sh
make db-lint
```

Then apply. Expect `Applied:` for each of the three:

``` sh
make db CMD=up
```

On the native stack, dbmate itself, as the migrator:

``` sh
dbmate --url "${MIGRATOR_URL}" -d migrations/sql --no-dump-schema up
```

## 7 Write the Schema, and Commit

Expect `Writing:`:

``` sh
make db CMD=dump
```

On the native stack,
`dbmate --url "${MIGRATOR_URL}" -d migrations/sql -s migrations/schema.sql dump`.

Run [the tests](3-tests.md) once more; expect
`8 of 8 pass`. Then commit the three migrations,
`schema.sql`, `box/project.json` and `test-3.sh`
together. Delete `users-draft.sql`: from here on, the
migrations are the truth, and a change to them is a new
migration.

## 8 What Reaches the Box

A release tag builds the migrations image and records
its digest; the manifest's change is handed to the
box's owner. No new host or image: `users` is a prefix
of py-api or js-api ([How a release reaches the
box](../../onboarding/ci-cd.md)). The box runs the
migrations once its PostgreSQL is there, the last step
of its `feature/postgres`; until then, the database is
your stack's alone.

## 9 See Also

- [The refinement](5-refinement.md): next
- [Write a
  migration](../../migrations/write-a-migration.md):
  the rules for a migration that changes a live table
