---
abstract: |
  A unit that was there before the users unit: its
  accessors take an owner and ask nobody. Give the
  people already using it a role, bring its
  permissions, write accessors that ask `users_may`
  beside the old ones, switch the service to them, and
  drop the old. Three releases, each safe for the code
  before it.
date: 2026-10-07
keywords:
- db
- migration
- authorisation
- users
- permissions
kind: how-to
sources:
- migrations/sql/20261006120000_py_api_begin.sql
- Makefile
status: draft
subtitle: Its permissions brought, its accessors
  asking, in three releases
title: Bring an Existing Unit under Authorisation
version: v0.1.0
---

## 1 Before You Start

- **The users unit, applied:** [tutorial
  3](../tutorials/3-the-migration/README.md)'s
  migrations, and `/users/me` in a service ([tutorial
  4](../tutorials/4-users/README.md)), which records
  each person at their sign-in. The UI calls it before
  anything else

- **A unit of your own, with live rows,** whose
  accessors take an owner from the service and check
  nothing: the first form in [the database's
  conduct](../conduct/database.md) §2. The examples
  here are py-api's bookmarks:

  ``` sql
  -- Before: whoever the service names owns the bookmark
  py_api_bookmark_add(p_owner text, p_url text) RETURNS bigint
  py_api_bookmarks_of(p_owner text) RETURNS TABLE (id bigint, url text, created_at timestamptz)
  ```

  If the service reads the table itself, write the
  accessors first, as their own release ([Write a
  migration](write-a-migration.md))

- **[Tutorial 5](../tutorials/5-notes/README.md),
  read.** It does all of this for a unit that starts
  under authorisation. This page adds the order that a
  unit already in use needs

## 2 The Shape

Migrations run before the new code starts, and the old
code may meet the new schema for a moment ([Write a
migration](write-a-migration.md) §9). So three
releases, each one safe for the code before it:

1.  **The schema.** Roles for the people already there
    (§3), the unit's permissions and its new accessors
    (§4), beside the old. The old code calls the old
    accessors and notices nothing
2.  **The service.** Its routes call the new accessors,
    with the caller from the token (§6)
3.  **The old accessors dropped,** once no released
    code calls them (§7)

## 3 Give the People Already There a Role

Today everyone who signs in may use the bookmarks.
Under the matrix, a person may do nothing until a role
says so (R1 of [tutorial
2](../tutorials/2-authorisation/1-concept.md) §4). Give
the role first, or the switch locks everyone out.

The roles are the users unit's, so this is a migration
under its prefix, as tutorial 3's first admin is. Two
statements: a starting role for people not yet seen,
and the role now for people already recorded. Expect
the new file's path:

``` sh
make db-new PREFIX=users NAME=everyone_a_member
```

``` sql
-- Everyone who signs in is a member: as before the users unit, when
-- every signed-in person could use every unit. A starting role for
-- people not yet seen, and the role now for people already recorded

-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';
INSERT INTO users_starting_roles (position, pattern, role) VALUES (90, '%', 'member')
ON CONFLICT DO NOTHING;
INSERT INTO users_members (sub, role)
  SELECT p.sub, 'member' FROM users_people p
ON CONFLICT DO NOTHING;

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
DELETE FROM users_starting_roles WHERE position = 90 AND pattern = '%';
```

- **`%` is what you had:** anyone with an account in
  the pool. If you meant fewer, say so now, with a
  narrower pattern ([tutorial
  2](../tutorials/2-authorisation/1-concept.md) §5);
  this is the moment it costs nothing
- **Position 90,** after any rule the project already
  has: the first match wins, so a narrower rule before
  it still decides
- **The down takes the rule away, not the roles.** Once
  given, a role is a person's, as any other; revoke it
  through `/users`

## 4 The Unit's Migration

The unit's own prefix, the unit's own file. Expect the
new file's path:

``` sh
make db-new PREFIX=py_api NAME=bookmarks_under_authorisation
```

In the up: the permissions, by the users unit's
published door, then the new accessors, each taking the
caller first and asking `users_may` before it acts.
**New names,** not the old ones replaced: the old code
still calls the old, and an old name that began to
refuse would fail it with a `500`. The down drops the
new accessors, then takes the permissions away:

``` sql
-- py-api's bookmarks under the users unit's matrix: bookmarks.read and
-- bookmarks.write, each person's own alone. New accessors take the
-- caller and ask users_may; the old, beside them, until py-api calls
-- the new (docs/migrations/bring-under-authorisation.md)

-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';
SELECT users_permission_add('bookmarks.read', 'reads their own bookmarks', '{reader,member}'),
       users_permission_add('bookmarks.write', 'keeps bookmarks of their own', '{member}');

-- A new bookmark, the caller its owner: bookmarks.write
CREATE OR REPLACE FUNCTION py_api_bookmark_new(p_caller text, p_url text) RETURNS bigint
  LANGUAGE plpgsql AS $$
DECLARE v_id bigint;
BEGIN
  IF NOT users_may(p_caller, 'bookmarks.write') THEN
    RAISE EXCEPTION 'bookmarks.write needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  INSERT INTO py_api_bookmarks (owner, url) VALUES (p_caller, p_url) RETURNING id INTO v_id;
  RETURN v_id;
END
$$;

-- The caller's own bookmarks, newest first: bookmarks.read
CREATE OR REPLACE FUNCTION py_api_bookmarks_mine(p_caller text, p_limit int DEFAULT 50)
  RETURNS TABLE (id bigint, url text, created_at timestamptz)
  LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
BEGIN
  IF NOT users_may(p_caller, 'bookmarks.read') THEN
    RAISE EXCEPTION 'bookmarks.read needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN QUERY
    SELECT b.id, b.url, b.created_at FROM py_api_bookmarks b
    WHERE b.owner = p_caller ORDER BY b.id DESC LIMIT least(p_limit, 500);
END
$$;

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_bookmarks_mine(text, int);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_bookmark_new(text, text);
SELECT users_permission_drop('bookmarks.write'), users_permission_drop('bookmarks.read');
```

- **The rows need nothing.** Their owner is already a
  `sub`, the same the users unit records
- **A table without an owner** gets one as any live
  column is added: nullable, with no rewrite ([Write a
  migration](write-a-migration.md) §8). The old rows
  are then nobody's; decide whether they stay readable
  to all, or are given owners from a record you already
  keep. Write that decision in the unit's concept
- **No `users_` table touched.** The roles of §3 are
  the users unit's own migration; this file calls the
  three published functions and nothing else of it

Expect `Found 0 issues`, then `Applied:` twice, the
users' file first:

``` sh
make db-lint
make db CMD=up
```

## 5 Test It

As [tutorial 5's
tests](../tutorials/5-notes/3-tests.md): one test a
rule, each failing before the migration, each on its
own people. Then one the new unit lacks: **nobody who
owns a row loses it.** Every owner may still read and
write. Expect no rows:

``` sh
psql "${MIGRATOR_URL}" -c "SELECT DISTINCT owner FROM py_api_bookmarks
WHERE NOT users_may(owner, 'bookmarks.read') OR NOT users_may(owner, 'bookmarks.write')"
```

A row here is a person the switch would shut out: one
the users unit has not yet recorded, since they have
not signed in since `/users/me` arrived, or one §3's
pattern does not match. Either is a decision, not a
bug: give them a role through `/users` once they sign
in, or accept it.

Release this, with the old code. Then run the query
again on the box's data before §6's release.

## 6 Switch the Service

In each route, the caller from the token, and the new
accessor; the refusals become HTTP as tutorial 5's
`run` turns them ([tutorial
5](../tutorials/5-notes/4-implementation.md) §4):

``` python
@app.get("/bookmarks")
def bookmarks(authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT * FROM py_api_bookmarks_mine(%s)", (who["sub"],))
    return r if isinstance(r, JSONResponse) else answer(r)
```

- **The service names the caller, never the owner.**
  The old route passed whoever it chose; the new one
  passes the token's `sub`, and the database decides
- **Each route gains a `403`.** Its shape is unchanged,
  and a caller holding a role never sees it; still, it
  is a change to a released contract. Write it in
  `api.md`, with the permission each route needs, and
  tell the UI's author in the merge request ([From an
  issue to a merge](../conduct/workflow.md) §4)
- **The unit's own tests** fake the new accessors'
  answers, a refusal among them, as tutorial 5's
  `database` does

## 7 Drop the Old Accessors

Once the release of §6 is on the box, and nothing of an
older release can start again, a third migration drops
the old pair:

``` sql
-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_bookmarks_of(text);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_bookmark_add(text, text);

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
```

Then, under the down's two `SET` lines, paste the two
`CREATE OR REPLACE FUNCTION` of the migration that
first made them, so a rollback on your machine can
run the old code.

Each drop names the old accessor's argument types, as
§1 shows them. Expect only the new pair:

``` sh
psql "${MIGRATOR_URL}" -c '\df py_api_bookmark*'
```

From here, no accessor of the unit acts without asking
the matrix.

## 8 What Can Go Wrong

- **`403` for everyone after the switch.** Nobody holds
  the permission: §3's migration did not run, or the
  roles in §4's `users_permission_add` are not the ones
  people hold. `users_matrix`, as an admin, shows which
  roles hold each permission
- **`403` for one person who used the unit yesterday.**
  The users unit has not recorded them: the UI did not
  call `/users/me` before the unit's routes. Call it
  first, at sign-in
- **The old code answers `500` during the release.** An
  old accessor was replaced in place, and now refuses.
  New names, as §4
- **`P0002`, `no such role`, applying.** The project
  has renamed or dropped `reader` or `member`. Name its
  own roles
- **`23514` applying.** A permission not
  `<unit>.<verb>`: `Bookmarks.read` or
  `bookmarks_read`. Lower case, one dot
- **An old accessor still there after §7.** Its drop
  names other argument types than the function has, and
  `IF EXISTS` passes over a function it does not find.
  `\df`, as §7, shows the types
- **A rollback refused, `42501`.** The down names a
  `users.` permission

## 9 See Also

- [Tutorial 5](../tutorials/5-notes/README.md): a unit
  under authorisation from its first migration
- [2 What each may
  do](../tutorials/2-authorisation/1-concept.md): the
  matrix, its rules and starting roles
- [Write a migration](write-a-migration.md): the
  mechanics, and a live table changed without locking
  it
- [The database's conduct](../conduct/database.md):
  what a unit may touch of another
