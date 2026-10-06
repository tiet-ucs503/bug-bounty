---
abstract: |
  What each person may do, decided in the database.
  Three sizes of rule: the trivial, which the manifest
  and an owner's column already answer; the general,
  low-complexity case, an access control matrix of
  roles and permissions, which this page builds; and
  the larger, which it points to. Notes become (u=rw,
  a=r): the owner writes, everyone who may read reads.
  All of it in SQL, tried in a transaction that is
  rolled back, and carried as it is into tutorial 3's
  migrations.
date: 2026-10-06
keywords:
- tutorial
- authz
- acm
- db
kind: tutorial
sources:
- migrations/sql/20261006120000_py_api_create_notes.sql
status: draft
subtitle: An access control matrix, in the database
title: "2 What Each May Do: Authorisation"
version: v0.1.0
---

## 1 Before You Start

- [1 Who comes in](1-authentication.md), with its
  `users-draft.sql`
- A local stack, up, with the template's own migration
  applied, as `make dev` and
  `tools/native-dev.sh start` do

## 2 Three Sizes of Rule

  ---------------------------------------------------------
  Size             What decides          Where
  ---------------- --------------------- ------------------
  **Trivial**      Signed in or not; the The manifest's
                   owner or not          `signed_in`;
                                         `owner = caller`
                                         in an accessor

  **Low            A role's permissions: An access control
  complexity, the  the access control    matrix in the
  general case**   matrix, plus the      database: this
                   trivial rules where   page
                   an object has an      
                   owner                 

  **Medium to      Relations between     A policy engine:
  high**           people and objects,   see §9
                   groups of groups,     
                   sharing, delegation,  
                   attributes, time      
  ---------------------------------------------------------

Most small projects never need the third. Start with
the second; move when you find yourself writing a role
per object, or a role per pair of people.

## 3 Draw the Matrix

Rows are roles; columns are permissions; a cell says
yes or nothing. A permission is `<unit>.<verb>`, named
for the unit that asks for it:

  --------------------------------------------------------------------------
  Role         `notes.read`   `notes.write`   `users.read`   `users.grant`
  ------------ -------------- --------------- -------------- ---------------
  `deny-all`                                                 

  `reader`     yes                                           

  `member`     yes            yes                            

  `admin`                                     yes            yes
  --------------------------------------------------------------------------

- **Roles add up.** A person may hold several; they may
  do what any of them may
- **No cell says no.** Nothing is allowed unless a role
  says so; `deny-all` is the row with nothing in it
- **`admin` does not read notes.** Running the people
  and reading their notes are different trusts. An
  admin who should read notes holds `member` too

## 4 Write the Matrix Down

Add this to the end of `users-draft.sql`, after
tutorial 1's part:

``` sql
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
```

- **`users_grants`:** the matrix, a row a yes
- **`users_may`:** the one question every unit asks:
  may this person do this? It is the users unit's one
  **published** function, marked so by its comment:
  other units call it, and nothing else of the users
  unit
- **`users_me`:** what the door answers: who you are,
  your roles, your permissions
- **`users_list`, `users_matrix`, `users_grant`,
  `users_revoke`:** the people and the matrix, read and
  changed. Each takes **the caller first**, asks
  `users_may`, and refuses before it acts
- **`users_revoke` keeps one `users.grant`:** the
  project cannot lock itself out by taking the last
  admin's role

## 5 Where the Check Lives

In the accessor, not in the service. The service says
who the caller is, from the token; the database decides
what they may do, and refuses with an SQLSTATE, which
the service turns into HTTP:

  ---------------------------------------------------------
  SQLSTATE   Name                       HTTP   Means
  ---------- -------------------------- ------ ------------
  `42501`    `insufficient_privilege`   403    Not allowed

  `P0002`    `no_data_found`            404    No such
                                               thing

  `23001`    `restrict_violation`       409    Would break
                                               a rule of
                                               the data

  `23514`    `check_violation`          400    A value out
                                               of bounds
  ---------------------------------------------------------

Why there: **a control that works without anyone being
careful.** A service that forgets to check cannot skip
it, because the accessor checks. A second service, in
another language, gets the same rules for nothing. And
it is one round trip: the question and the act in one
call.

## 6 Notes as (u=rw, a=r)

The template's `py_api_notes` has an `owner`. Read it
as a Unix mode: **u**, the owner, reads and writes;
**a**, all, read. Here "all" is everyone the matrix
gives `notes.read`, and "writes" needs the owner
**and** `notes.write`: the matrix says who may use
notes at all; the owner's column says whose note it is.

Save the notes' part as `notes-draft.sql`. Its names
carry `py_api_`, py-api's prefix: the notes are
py-api's, and only ask the users unit, through
`users_may`:

``` sql
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
```

- **`py_api_note_new`:** `notes.write`; the caller owns
  the note
- **`py_api_notes_all`:** `notes.read`; every note,
  saying only whether it is the caller's, never whose
- **`py_api_note_edit`, `py_api_note_drop`:**
  `notes.write`, and the owner. A note that exists but
  is another's is `42501`; one that does not is `P0002`
- **The example's `py_api_note_add` and
  `py_api_notes_of` stay** as they are. An accessor's
  signature is a promise: the new ones sit beside them

## 7 Try It

Save the trial as `try-2.sql`:

``` sql
-- Three people in; you made admin by hand, as tutorial 3's first admin will be
SELECT users_admit('you', 'you@example.org', true), users_admit('alice', 'alice@example.org', true),
       users_admit('bob', 'bob@elsewhere.net', true);
INSERT INTO users_members (sub, role) VALUES ('you', 'admin');

-- The matrix, asked and changed
SELECT users_may('bob', 'notes.read') AS bob_reads;
SELECT users_grant('you', 'bob', 'reader'), users_grant('you', 'alice', 'member');
SELECT users_may('bob', 'notes.read') AS bob_reads, users_may('bob', 'notes.write') AS bob_writes;
SELECT * FROM users_me('bob');

-- A note, (u=rw, a=r): alice's to change, everyone's to read
SELECT py_api_note_new('alice', 'a first note');
SELECT py_api_note_edit('alice', max(id), 'a first note, edited') FROM py_api_notes;
SELECT body, mine FROM py_api_notes_all('bob');

-- Refusals, each caught so the next one runs
DO $$ BEGIN
  PERFORM py_api_note_new('bob', 'bob writes');
EXCEPTION WHEN insufficient_privilege THEN RAISE NOTICE 'bob, a reader, writes a note: %', SQLERRM;
END $$;
DO $$ BEGIN
  PERFORM users_grant('bob', 'bob', 'admin');
EXCEPTION WHEN insufficient_privilege THEN RAISE NOTICE 'bob makes himself admin: %', SQLERRM;
END $$;

-- Bob a member now: he writes notes, but alice's is still hers
SELECT users_grant('you', 'bob', 'member');
DO $$ BEGIN
  PERFORM py_api_note_edit('bob', (SELECT max(id) FROM py_api_notes), 'bob was here');
EXCEPTION WHEN insufficient_privilege THEN RAISE NOTICE 'bob, a member, edits alice''s note: %', SQLERRM;
END $$;
```

Then run the three drafts in one transaction, rolled
back:

``` sh
psql "${MIGRATOR_URL}" -q -v ON_ERROR_STOP=1 -c BEGIN -f users-draft.sql -f notes-draft.sql -f try-2.sql -c ROLLBACK
```

Expect, in order:

- three `t`: everyone is in, by tutorial 1's `%` rule;
- `bob_reads` `f`: `deny-all` alone reads nothing;
- after the grants, `t` and `f`: bob reads and does not
  write; `users_me` shows his two roles and
  `{notes.read}`;
- alice's note, edited, read by bob with `mine` `f`;
- three notices: bob, a reader, may not write; may not
  make himself admin; and, a member now, may not edit
  alice's note: `not your note`.

## 8 What Can Go Wrong

- **`function users_may(text, text) does not exist`.**
  `notes-draft.sql` ran before `users-draft.sql`. A
  function in `LANGUAGE sql` is checked when it is
  made; give the files in order
- **Every check fails for someone you granted.** The
  role has no row in `users_grants` for that
  permission:
  `SELECT * FROM users_grants WHERE role = 'member'`
- **A permission's name is refused by a `CHECK`.** It
  must be `<unit>.<verb>`, lower case, one dot
- **You want "everyone but bob".** A matrix cannot say
  no. Take bob's role, or give the others a role he
  lacks. If you need refusals that override grants, you
  are in §2's third row

## 9 See Also

- [3 Make it a migration](3-the-migration.md): next
- [OWASP's Authorization Cheat
  Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html):
  deny by default, check every request, and the rest,
  for any size
- For the medium-to-high row: [OpenFGA's concepts of
  authorisation](https://openfga.dev/docs/authorization-concepts),
  relation-based, after Google's
  [Zanzibar](https://research.google/pubs/zanzibar-googles-consistent-global-authorization-system/);
  and [Cedar](https://www.cedarpolicy.com/), policies
  over attributes. Read 2026-10-06
- [The database's conduct](../conduct/database.md):
  what a unit publishes, and what it may call
