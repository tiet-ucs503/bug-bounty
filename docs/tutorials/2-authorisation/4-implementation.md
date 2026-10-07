---
abstract: |
  Step 4 of tutorial 2: the SQL that makes the 27 tests
  pass, a piece at a time, each piece justified by the
  rules it keeps and the tests it answers. The matrix
  and its accessors at the end of `users-draft.sql`,
  with the two functions a unit's migration calls to
  bring its permissions and take them away.
date: 2026-10-07
keywords:
- tutorial
- authz
- acm
- db
kind: tutorial
sources:
- tools/native-dev.sh
status: draft
subtitle: Step 4, the code
title: "2.4 What Each May Do: the Implementation"
version: v0.1.0
---

## 1 Before You Start

- [The contract](2-contract.md): every signature below
  is one of its rows
- [The tests](3-tests.md), saved as `test-2.sql`, run
  once and failing

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

First the permissions there are, its columns. A unit
brings each of its own (R7); the `CHECK` holds every
one to `<unit>.<verb>` (R9, T2.24):

``` sql
-- The permissions there are, each brought by the unit that asks for
-- it. A permission is <unit>.<verb>: users.grant, notes.read
CREATE TABLE IF NOT EXISTS users_permissions (
  permission text PRIMARY KEY CHECK (permission ~ '^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*$'),
  about text NOT NULL DEFAULT ''
);
```

Then the matrix. One row for each cell that says yes,
so a cell that says no cannot be written (R1). Both
keys are foreign, so a permission taken away takes its
cells with it (T2.19):

``` sql
-- The access control matrix: one row for each cell that says yes
CREATE TABLE IF NOT EXISTS users_grants (
  role text NOT NULL REFERENCES users_roles (role) ON DELETE CASCADE,
  permission text NOT NULL REFERENCES users_permissions (permission) ON DELETE CASCADE,
  PRIMARY KEY (role, permission)
);
CREATE INDEX IF NOT EXISTS users_grants_permission_idx ON users_grants (permission);
```

## 4 The One Question

`users_may` is what every rule comes down to: does any
of this person's roles hold this permission? `EXISTS`
over a join, so no role means no (R1, T2.1, T2.2), and
any role is enough (R3, T2.7). Its comment marks it
**published**, one of the three functions of the users
unit that other units may call (R8, T2.23):

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

## 10 A Unit's Permissions

The other two published functions, for a unit's
migrations. Adding checks every role first, so a role
that does not exist is `P0002`, not a foreign key's
error (T2.18); both inserts do nothing on a conflict,
so twice is once (T2.17). It takes no caller: a
migration runs for the project, not for a person (R7):

``` sql
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
```

Taking away deletes the permission; §3's cascade takes
its cells, and nothing else (T2.19, T2.20). Deleting
what is not there deletes nothing, so twice is once
(T2.21). The users unit's own are refused, or a unit's
migration could lock the project out, which R5 forbids
(T2.22):

``` sql
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
```

## 11 What the Project Starts With

Three roles, and the users unit's own two permissions,
brought the way any unit brings its own (R2, T2.3 to
T2.5). `reader` and `member` hold nothing until a unit
gives them something; the tests' `example` unit does,
and tutorial 5's notes will. No starting roles: until
you add one, everyone signs in with none, and an admin
gives roles:

``` sql
-- The roles the project starts with, and the users unit's own
-- permissions; no starting roles
INSERT INTO users_roles (role, about) VALUES
  ('reader', 'reads what each unit lets it'),
  ('member', 'reads and writes what each unit lets it'),
  ('admin', 'reads the people and the matrix, grants and revokes roles')
ON CONFLICT DO NOTHING;
```

``` sql
SELECT users_permission_add('users.read', 'reads the people and the matrix', '{admin}'),
       users_permission_add('users.grant', 'grants and revokes roles', '{admin}');
```

## 12 See Also

- [The refinement](5-refinement.md): next, run the
  tests
- [The database's conduct](../../conduct/database.md):
  prefixes, accessors, and what a unit publishes
