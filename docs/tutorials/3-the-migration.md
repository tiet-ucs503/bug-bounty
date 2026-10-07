---
abstract: |
  Tutorials 1 and 2's drafts, carried as they are into
  migrations: one for the users unit, one for its first
  admin, one for the notes. The unit's prefix given to
  the service that will serve it; each file complete
  and consistent, linted, applied, rolled back and
  applied again, and the schema written down.
date: 2026-10-06
keywords:
- tutorial
- db
- migration
- dbmate
- authz
kind: tutorial
sources:
- migrations/sql/20261006120000_py_api_create_notes.sql
- box/render.py
- Makefile
status: draft
subtitle: The drafts, as migrations the box will run
title: 3 Make It a Migration
version: v0.1.0
---

`[NO:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` --- what
these mean, and what they do not: [the tutorials'
page](README.md) §5.

> [!WARNING]
> Written for an earlier tutorial 1, which let people
> in by admission rules and gave everyone `deny-all`.
> Tutorials 1 and 2 have since moved roles and
> starting roles into tutorial 2. This page is next to
> be reworked; until then it does not run as written.

## 1 Before You Start

- [What you need](README.md) §2, installed and checked
- `users-draft.sql` and `notes-draft.sql`, from
  tutorials [1](1-authentication.md) and
  [2](2-authorisation/README.md)
- A local stack, up
- [Write a
  migration](../migrations/write-a-migration.md) is the
  how-to; this page follows it

## 2 Give the Unit Its Prefix

A migration's names carry a prefix the manifest gives a
service, and `make check` refuses any other. `/users`
will be routes of the service you write it in: py-api,
for tutorial 4's Python, or js-api, for tutorial 5's
JavaScript. Not a service of its own: that would be a
host, an image and a build more, and memory from the
box's 1 GiB, for five routes.

So that service owns the `users` prefix beside its own.
In `box/project.json`, py-api's `"prefix": "py_api"`
becomes, its own first:

``` json
"prefixes": ["py_api", "users"],
```

For JavaScript, js-api's
`"prefixes": ["js_api", "users"]`. Expect the two
services as before, agreeing with `services/`:

``` sh
make check
```

## 3 The Users Migration

Make the file. Expect its path,
`migrations/sql/<time>_users_create_tables.sql`:

``` sh
make db-new PREFIX=users NAME=create_tables
```

Under `-- migrate:up`, after the two `SET` lines, the
whole of `users-draft.sql`, as it is. Under
`-- migrate:down`, its undoing: every function, then
every table, each in the reverse of the order it was
made, since a table cannot go before those that refer
to it. The file, whole:

``` sql
-- The users unit: who may come in, and what each person may do
-- (docs/tutorials/1-authentication.md, 2-authorisation/). Every name
-- carries the prefix users_. Other units call users_may alone, the one
-- function published for them (docs/conduct/database.md §3).

-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';

-- The roles. deny-all grants nothing: whoever holds it alone may do
-- nothing, as if signed out
CREATE TABLE IF NOT EXISTS users_roles (
  role text PRIMARY KEY CHECK (role ~ '^[a-z][a-z0-9-]{1,30}$'),
  about text NOT NULL DEFAULT ''
);

-- Who may come in, and with which role: the first rule, by position,
-- whose pattern the verified e-mail is LIKE. No rule, no entry
CREATE TABLE IF NOT EXISTS users_admission (
  position bigint PRIMARY KEY,
  pattern text NOT NULL CHECK (pattern = lower(pattern)),
  role text NOT NULL REFERENCES users_roles (role)
);

-- The people admitted, by Cognito's sub
CREATE TABLE IF NOT EXISTS users_people (
  sub text PRIMARY KEY,
  email text NOT NULL,
  admitted_at timestamptz NOT NULL DEFAULT now(),
  seen_at timestamptz NOT NULL DEFAULT now()
);

-- Who holds which role
CREATE TABLE IF NOT EXISTS users_members (
  sub text NOT NULL REFERENCES users_people (sub) ON DELETE CASCADE,
  role text NOT NULL REFERENCES users_roles (role) ON DELETE CASCADE,
  PRIMARY KEY (sub, role)
);
CREATE INDEX IF NOT EXISTS users_members_role_idx ON users_members (role);

-- The door. Someone already in is seen again; someone new comes in if
-- their e-mail is verified and a rule matches it, with that rule's
-- role. True if the person is in
CREATE OR REPLACE FUNCTION users_admit(p_sub text, p_email text, p_verified boolean) RETURNS boolean
  LANGUAGE plpgsql AS $$
DECLARE
  v_role text;
BEGIN
  UPDATE users_people SET seen_at = now() WHERE sub = p_sub;
  IF FOUND THEN
    RETURN true;
  END IF;
  IF NOT p_verified OR coalesce(p_email, '') = '' THEN
    RETURN false;
  END IF;
  SELECT a.role INTO v_role FROM users_admission a
    WHERE lower(p_email) LIKE a.pattern ORDER BY a.position LIMIT 1;
  IF v_role IS NULL THEN
    RETURN false;
  END IF;
  INSERT INTO users_people (sub, email) VALUES (p_sub, lower(p_email)) ON CONFLICT (sub) DO NOTHING;
  INSERT INTO users_members (sub, role) VALUES (p_sub, v_role) ON CONFLICT DO NOTHING;
  RETURN true;
END
$$;

-- The roles the project starts with; what each may do is tutorial 2's
INSERT INTO users_roles (role, about) VALUES
  ('deny-all', 'admitted, and may do nothing: where everyone starts'),
  ('reader', 'reads notes'),
  ('member', 'reads and writes notes'),
  ('admin', 'reads the people and the matrix, grants and revokes roles')
ON CONFLICT DO NOTHING;

-- Everyone may come in, and starts as deny-all
INSERT INTO users_admission (position, pattern, role) VALUES
  (100, '%', 'deny-all')
ON CONFLICT DO NOTHING;

-- The access control matrix: one row for each cell that says yes. A
-- permission is <unit>.<verb>: notes.read, users.grant
CREATE TABLE IF NOT EXISTS users_grants (
  role text NOT NULL REFERENCES users_roles (role) ON DELETE CASCADE,
  permission text NOT NULL CHECK (permission ~ '^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*$'),
  PRIMARY KEY (role, permission)
);

-- Published, for every unit: may this person do this?
CREATE OR REPLACE FUNCTION users_may(p_sub text, p_permission text) RETURNS boolean
  LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM users_members m JOIN users_grants g ON g.role = m.role
    WHERE m.sub = p_sub AND g.permission = p_permission)
$$;
COMMENT ON FUNCTION users_may(text, text) IS 'published: may this person do this? Called by every unit';

-- The caller: e-mail, roles and permissions; no row if not admitted
CREATE OR REPLACE FUNCTION users_me(p_sub text)
  RETURNS TABLE (sub text, email text, roles text[], permissions text[])
  LANGUAGE sql STABLE AS $$
  SELECT p.sub, p.email,
    coalesce((SELECT array_agg(m.role ORDER BY m.role) FROM users_members m WHERE m.sub = p.sub), '{}'),
    coalesce((SELECT array_agg(DISTINCT g.permission ORDER BY g.permission)
              FROM users_members m JOIN users_grants g ON g.role = m.role WHERE m.sub = p.sub), '{}')
  FROM users_people p WHERE p.sub = p_sub
$$;

-- Everyone admitted, with their roles: users.read
CREATE OR REPLACE FUNCTION users_list(p_caller text)
  RETURNS TABLE (sub text, email text, roles text[], admitted_at timestamptz, seen_at timestamptz)
  LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
BEGIN
  IF NOT users_may(p_caller, 'users.read') THEN
    RAISE EXCEPTION 'users.read needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN QUERY
    SELECT p.sub, p.email, coalesce(array_agg(m.role ORDER BY m.role) FILTER (WHERE m.role IS NOT NULL), '{}'),
           p.admitted_at, p.seen_at
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

-- The matrix the project starts with
INSERT INTO users_grants (role, permission) VALUES
  ('reader', 'notes.read'),
  ('member', 'notes.read'),
  ('member', 'notes.write'),
  ('admin', 'users.read'),
  ('admin', 'users.grant')
ON CONFLICT DO NOTHING;

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
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
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS users_admit(text, text, boolean);
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS users_members;
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS users_people;
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS users_admission;
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS users_grants;
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS users_roles;
```

The draft was already written to run twice:
`IF NOT EXISTS` on every table and index, `OR REPLACE`
on every function, `ON CONFLICT DO NOTHING` on every
seed. A migration that fails part way runs again.

## 4 Complete

A unit's migration is complete when nothing it makes is
left without a way to use it, and nothing it names is
missing. Check it against the draft's own parts:

  ----------------------------------------------------
  Every              Has
  ------------------ ---------------------------------
  Table              An accessor that writes it, and
                     one that reads it

  Accessor that acts A permission it asks `users_may`
  for a caller       for, and a role in the seeds that
                     holds it

  Role in a seed     A row in `users_roles`

  Object the up      A `DROP` in the down
  makes              
  ----------------------------------------------------

Once applied (§8), list what the unit made; expect five
tables, the index and seven functions, all `users_*`:

``` sh
psql "${MIGRATOR_URL}" -c "SELECT 'table' AS kind, tablename AS name FROM pg_tables WHERE tablename LIKE 'users\_%' UNION ALL SELECT 'index', indexname FROM pg_indexes WHERE indexname LIKE 'users\_%\_idx' UNION ALL SELECT 'function', proname FROM pg_proc WHERE proname LIKE 'users\_%' ORDER BY 1, 2"
```

## 5 Consistent

The data keeps its own rules, so no caller has to:

- **Primary keys:** one membership a person and role,
  one grant a role and permission, one rule a position
- **Foreign keys:** no grant, member or rule for a role
  that does not exist; no member who is not a person. A
  role deleted takes its grants and memberships with
  it; a role in a rule cannot be deleted
- **`CHECK`s:** a role's name, a permission's
  `<unit>.<verb>`, a rule's pattern in lower case
- **The last `users.grant`:** `users_revoke` refuses to
  take it, `23001`

Try one, in a transaction rolled back. Expect
`violates foreign key constraint`:

``` sh
psql "${MIGRATOR_URL}" -c BEGIN -c "INSERT INTO users_grants VALUES ('nobody', 'notes.read')" -c ROLLBACK
```

## 6 The First Admin

Everyone comes in as `deny-all`, and only an admin
gives roles: someone must be the first. A migration of
its own, so it is the one place your address is
written. Make it:

``` sh
make db-new PREFIX=users NAME=first_admin
```

And write, with **your** address for `you@example.org`:

``` sql
-- The project's first admin, by e-mail: admitted as admin at their
-- first sign-in, or made admin now if already in. Your own address:
-- the repository holds it, so mind who can read the repository
-- (docs/tutorials/3-the-migration.md §5).

-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';
INSERT INTO users_admission (position, pattern, role) VALUES (1, 'you@example.org', 'admin')
ON CONFLICT DO NOTHING;
INSERT INTO users_members (sub, role)
  SELECT p.sub, 'admin' FROM users_people p WHERE p.email = 'you@example.org'
ON CONFLICT DO NOTHING;

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
DELETE FROM users_admission WHERE position = 1 AND pattern = 'you@example.org';
```

A rule at position 1, before every other: at your first
sign-in, you come in as `admin`. If you are in already,
the second statement makes you one now.

> [!WARNING]
> The address is in the repository for good, and in its
> history. If the repository is public, so is it. An
> address made for the role keeps your own out of it.

## 7 The Notes Migration

py-api's prefix, py-api's file:

``` sh
make db-new PREFIX=py_api NAME=notes_permissions
```

Under `-- migrate:up`, `notes-draft.sql` as it is;
under `-- migrate:down`, its undoing:

``` sql
-- Notes under the matrix and their owners, (u=rw, a=r): everyone with
-- notes.read reads every note; the owner alone changes theirs, and only
-- while they hold notes.write (docs/tutorials/2-authorisation/). Each
-- accessor takes the caller first and checks before it acts. The
-- example's py_api_note_add and py_api_notes_of stay as they are:
-- their signatures are a promise; nothing new calls them.

-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';
ALTER TABLE py_api_notes ADD COLUMN IF NOT EXISTS updated_at timestamptz;

-- A new note, the caller its owner: notes.write
CREATE OR REPLACE FUNCTION py_api_note_new(p_caller text, p_body text) RETURNS bigint
  LANGUAGE plpgsql AS $$
BEGIN
  IF NOT users_may(p_caller, 'notes.write') THEN
    RAISE EXCEPTION 'notes.write needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN py_api_note_add(p_caller, p_body);
END
$$;

-- Every note, newest first, a page at a time: notes.read. Not who
-- owns each, only whether the caller does
CREATE OR REPLACE FUNCTION py_api_notes_all(p_caller text, p_before bigint DEFAULT NULL, p_limit int DEFAULT 50)
  RETURNS TABLE (id bigint, body text, mine boolean, created_at timestamptz, updated_at timestamptz)
  LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
BEGIN
  IF NOT users_may(p_caller, 'notes.read') THEN
    RAISE EXCEPTION 'notes.read needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN QUERY
    SELECT n.id, n.body, n.owner = p_caller, n.created_at, n.updated_at FROM py_api_notes n
    WHERE p_before IS NULL OR n.id < p_before ORDER BY n.id DESC LIMIT least(p_limit, 200);
END
$$;

-- The owner's change to their note: notes.write, and theirs
CREATE OR REPLACE FUNCTION py_api_note_edit(p_caller text, p_id bigint, p_body text) RETURNS void
  LANGUAGE plpgsql AS $$
BEGIN
  IF NOT users_may(p_caller, 'notes.write') THEN
    RAISE EXCEPTION 'notes.write needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  UPDATE py_api_notes SET body = p_body, updated_at = now() WHERE id = p_id AND owner = p_caller;
  IF NOT FOUND THEN
    IF EXISTS (SELECT 1 FROM py_api_notes WHERE id = p_id) THEN
      RAISE EXCEPTION 'not your note' USING ERRCODE = 'insufficient_privilege';
    END IF;
    RAISE EXCEPTION 'no such note' USING ERRCODE = 'no_data_found';
  END IF;
END
$$;

-- The owner's removal of their note: notes.write, and theirs
CREATE OR REPLACE FUNCTION py_api_note_drop(p_caller text, p_id bigint) RETURNS void
  LANGUAGE plpgsql AS $$
BEGIN
  IF NOT users_may(p_caller, 'notes.write') THEN
    RAISE EXCEPTION 'notes.write needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  DELETE FROM py_api_notes WHERE id = p_id AND owner = p_caller;
  IF NOT FOUND THEN
    IF EXISTS (SELECT 1 FROM py_api_notes WHERE id = p_id) THEN
      RAISE EXCEPTION 'not your note' USING ERRCODE = 'insufficient_privilege';
    END IF;
    RAISE EXCEPTION 'no such note' USING ERRCODE = 'no_data_found';
  END IF;
END
$$;

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_note_drop(text, bigint);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_note_edit(text, bigint, text);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_notes_all(text, bigint, int);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_note_new(text, text);
-- squawk-ignore ban-drop-column
ALTER TABLE py_api_notes DROP COLUMN IF EXISTS updated_at;
```

Its file name sorts after the users migration's, so it
runs after: its `py_api_note_*` call `users_may`, which
must exist first.

## 8 Lint, and Apply

Expect `Found 0 issues`:

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

Then §4's list.

## 9 Prove the Downs

> [!CAUTION]
> A rollback runs the down, and its rows go with what
> it drops: every person, role and note the three made.
> On your machine, that is test data alone.

Note the schema as it stands:

``` sh
pg_dump -s --no-owner --no-privileges "${MIGRATOR_URL}" | grep -v '^\\\|^--\|^$' > /tmp/after-up.sql
```

Roll the three back, newest first. Expect
`Rolled back:` three times:

``` sh
make db CMD=rollback
make db CMD=rollback
make db CMD=rollback
```

The schema now should be the template's, as
`migrations/schema.sql` was before you began. Expect no
output:

``` sh
diff <(pg_dump -s --no-owner --no-privileges "${MIGRATOR_URL}" | grep -v '^\\\|^--\|^$') <(git show HEAD:migrations/schema.sql | grep -v '^\\\|^--\|^$\|^INSERT\|^    (')
```

Apply them again, and expect the schema exactly as it
was, no output:

``` sh
make db CMD=up
diff <(pg_dump -s --no-owner --no-privileges "${MIGRATOR_URL}" | grep -v '^\\\|^--\|^$') /tmp/after-up.sql
```

On the native stack,
`dbmate --url "${MIGRATOR_URL}" -d migrations/sql --no-dump-schema rollback`
for `make db CMD=rollback`, and `up` for `up`.

## 10 Write the Schema, and Commit

Expect `Writing:`:

``` sh
make db CMD=dump
```

On the native stack,
`dbmate --url "${MIGRATOR_URL}" -d migrations/sql -s migrations/schema.sql dump`.

Commit the three migrations, `schema.sql` and
`box/project.json` together. Delete the drafts: from
here on, the migrations are the truth, and a change to
them is a new migration.

## 11 What Reaches the Box

A release tag builds the migrations image and records
its digest; the manifest's change is handed to the
box's owner. No new host or image: `users` is a prefix
of py-api or js-api ([How a release reaches the
box](../onboarding/ci-cd.md)). The box runs the
migrations once its PostgreSQL is there, the last step
of its `feature/postgres`; until then, the database is
your stack's alone.

## 12 What Can Go Wrong

- **`make check`:
  `not <14-digit version>_<prefix>_<what>.sql`.**
  `users` is not among a service's `prefixes` yet, §2;
  or the file was named by hand
- **`function users_may(text, text) does not exist`,
  applying the notes.** Its file sorts before the users
  migration's. Rename it with a later time; nothing has
  run anywhere else yet
- **The diff after the rollbacks shows `GRANT` lines.**
  `--no-privileges` is missing: the dev stack's logins
  hold grants that `schema.sql` does not record
- **`permission denied for table schema_migrations`, as
  the services' login.** As meant: only the migrator
  writes dbmate's ledger
- **A table you expect is missing, and the migration
  shows `[X]`.** It was edited after it ran. Write a
  new one

## 13 See Also

- [4 users in Python](4-users-in-python.md), or [5 in
  JavaScript](5-users-in-javascript.md): next
- [Write a
  migration](../migrations/write-a-migration.md)
- [The database's conduct](../conduct/database.md)
