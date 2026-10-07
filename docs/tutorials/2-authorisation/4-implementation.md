---
abstract: |
  Step 4 of tutorial 2: the SQL that makes the 27 tests
  pass, a piece at a time, each piece justified by the
  rules it keeps and the tests it answers. The matrix
  and its accessors at the end of `users-draft.sql`;
  the notes' accessors in `notes-draft.sql`.
date: 2026-10-07
keywords:
- tutorial
- authz
- acm
- db
kind: tutorial
sources:
- migrations/sql/20261006120000_py_api_create_notes.sql
status: draft
subtitle: Step 4, the code
title: "2.4 What Each May Do: the Implementation"
version: v0.1.0
---

## 1 Before You Start

- [The tests](2-tests.md), saved as `test-2.sql`, run
  once and failing
- [The contract](3-contract.md): every signature below
  is one of its rows

Each piece below is added, in order, to the end of a
file. Run the tests after any piece, if you like: the
count of passes only grows.

## 2 The Roles, and Who Holds Them

Add to the end of `users-draft.sql`, after tutorial 1's
part. A role is a name; a person holds any number of
them (R3). Nobody holds one unless it is given, so a
person who signed in may do nothing yet (R1):

``` sql
-- The roles. A person who holds none may do nothing
CREATE TABLE IF NOT EXISTS users_roles (
  role text PRIMARY KEY CHECK (role ~ '^[a-z][a-z0-9-]{1,30}$'),
  about text NOT NULL DEFAULT ''
);
```

Who holds which. Both keys are foreign, so a role is
held only by a person who signed in, and only if the
role exists (R4); deleting either deletes the holding:

``` sql
-- Who holds which role
CREATE TABLE IF NOT EXISTS users_members (
  sub text NOT NULL REFERENCES users_people (sub) ON DELETE CASCADE,
  role text NOT NULL REFERENCES users_roles (role) ON DELETE CASCADE,
  PRIMARY KEY (sub, role)
);
CREATE INDEX IF NOT EXISTS users_members_role_idx ON users_members (role);
```

## 3 The Matrix, a Table

Then the matrix. One row for each cell that says yes,
so a cell that says no cannot be written (R1); the
`CHECK` holds every permission to `<unit>.<verb>` (R9,
T2.24):

``` sql
-- The access control matrix: one row for each cell that says yes. A
-- permission is <unit>.<verb>: notes.read, users.grant
CREATE TABLE IF NOT EXISTS users_grants (
  role text NOT NULL REFERENCES users_roles (role) ON DELETE CASCADE,
  permission text NOT NULL CHECK (permission ~ '^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*$'),
  PRIMARY KEY (role, permission)
);
```

## 4 The One Question

`users_may` is what every rule comes down to: does any
of this person's roles hold this permission? `EXISTS`
over a join, so no role means no (R1, T2.1, T2.2), and
any role is enough (R3, T2.7). Its comment marks it
**published**, the users unit's one function that other
units may call:

``` sql
-- Published, for every unit: may this person do this?
CREATE OR REPLACE FUNCTION users_may(p_sub text, p_permission text) RETURNS boolean
  LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM users_members m JOIN users_grants g ON g.role = m.role
    WHERE m.sub = p_sub AND g.permission = p_permission)
$$;
COMMENT ON FUNCTION users_may(text, text) IS 'published: may this person do this? Called by every unit';
```

## 5 Who You Are

What the door answers, in tutorial 4: the caller's
roles and permissions, sorted. No permission is needed
to ask about yourself; someone never signed in gets no
row (T2.15):

``` sql
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
```

## 6 The People and the Matrix

Both need `users.read`, and both ask before they read
(R6, T2.6, T2.14). `#variable_conflict use_column` lets
the column `sub` mean the table's, not the function's
output of the same name:

``` sql
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
```

``` sql
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
```

## 7 Give a Role

`users.grant` first (R4, T2.8). Then the person and the
role must exist, each refused with `P0002`, so the
service answers `404`, not a foreign key's error (T2.9,
T2.10). `ON CONFLICT DO NOTHING` makes twice the same
as once (T2.11):

``` sql
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
```

## 8 Take a Role Away

The delete first, then the check that some
`users.grant` is left; if none is, the exception rolls
the delete back with it (R5, T2.12). Any other revoke
goes through (T2.13):

``` sql
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
```

## 9 Starting Roles

R10, in two pieces. The rules, read like a person's
first sign-in reads them: by position, lowest first,
the first `LIKE` match giving its role. Patterns are
lower case, so an address in any case matches:

``` sql
-- Starting roles: at a person's first sign-in, the first rule by
-- position whose pattern their e-mail is LIKE gives its role. Read
-- once; no match, no role
CREATE TABLE IF NOT EXISTS users_starting_roles (
  position bigint PRIMARY KEY,
  pattern text NOT NULL CHECK (pattern = lower(pattern)),
  role text NOT NULL REFERENCES users_roles (role) ON DELETE CASCADE
);
```

The trigger is what keeps authentication and
authorisation apart. Tutorial 1's `users_person_see`
records a person and knows nothing of roles. This
trigger runs after it, once, when the person's row is
first inserted, and never on the updates of later
sign-ins (T2.25 to T2.27):

``` sql
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
```

Which rules to write is [the concept](1-concept.md)'s
§5, which also has a query to try them on.

## 10 What the Project Starts With

Three roles, and §3 of [the concept](1-concept.md), row
by row (R2, T2.3 to T2.5). No starting roles: until you
add one, everyone signs in with none, and an admin
gives roles:

``` sql
-- The roles and the matrix the project starts with; no starting roles
INSERT INTO users_roles (role, about) VALUES
  ('reader', 'reads notes'),
  ('member', 'reads and writes notes'),
  ('admin', 'reads the people and the matrix, grants and revokes roles')
ON CONFLICT DO NOTHING;
```

``` sql
INSERT INTO users_grants (role, permission) VALUES
  ('reader', 'notes.read'),
  ('member', 'notes.read'),
  ('member', 'notes.write'),
  ('admin', 'users.read'),
  ('admin', 'users.grant')
ON CONFLICT DO NOTHING;
```

## 11 The Notes

Save the notes' part as `notes-draft.sql`. Its names
carry `py_api_`, py-api's prefix: the notes are
py-api's, and ask the users unit only through
`users_may`.

When a note was last changed, for the dashboard:

``` sql
ALTER TABLE py_api_notes ADD COLUMN IF NOT EXISTS updated_at timestamptz;
```

A new note: `notes.write`, and the caller owns it (R7,
T2.16, T2.17). It calls the template's own
`py_api_note_add`, kept as it is:

``` sql
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
```

Every note, a page at a time: `notes.read`. It answers
`mine`, a comparison, so the owner never leaves the
database (R8, T2.22, T2.23):

``` sql
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
```

Edit and delete: `notes.write`, and the owner, in the
`WHERE` (R7, T2.18 to T2.20). When nothing matched, the
accessor asks why, so another's note and no note answer
differently (T2.19, T2.21):

``` sql
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
```

``` sql
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
```

## 12 See Also

- [The refinement](5-refinement.md): next, run the
  tests
- [The database's conduct](../../conduct/database.md):
  prefixes, accessors, and what a unit publishes
