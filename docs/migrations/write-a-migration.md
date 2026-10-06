---
abstract: |
  Change the project's database: write a migration with
  dbmate, its names under a service's prefix, lint it
  with Squawk, apply and roll it back in the dev stack,
  commit it with the schema it makes, and release it.
  With the patterns that change a live table without
  locking it.
date: 2026-10-06
keywords:
- db
- migration
- dbmate
- squawk
- postgres
kind: how-to
sources:
- migrations/sql/20261006120000_py_api_create_notes.sql
- migrations/.squawk.toml
- box/render.py
- Makefile
status: draft
subtitle: dbmate's plain SQL, Squawk's lint, one change
  at a time
title: Write a Migration
version: v0.1.0
---

## 1 Before You Start

- **The box has no database yet.** Its PostgreSQL, and
  a project's database on it, is the last step of the
  box's `feature/postgres` (the box's `todo.md` §50.2
  decision 5). Until then a schema lives in the dev
  stack alone. A migration written now runs on the box
  unchanged, the same way, once that step is done
- **The project asks for its database:**
  `"database": true` in `box/project.json`.
  `make check` then holds `migrations/sql/` to the
  manifest
- **The dev stack,** [A local stack that mirrors the
  box](../onboarding/local-dev.md); or PostgreSQL and
  dbmate without Docker, §10
- **Node,** for Squawk, which npm fetches
- **The discipline:** [The database's
  conduct](../conduct/database.md), names under a
  prefix and accessors in the database

## 2 Write One

A file named by the time it is made and the prefix of
the service whose objects it makes. Expect the new
file's path:

``` sh
make db-new PREFIX=py_api NAME=notes_add_title
```

Write the change under `-- migrate:up`, and its undoing
under `-- migrate:down`. Keep the two `SET` lines the
file starts with, in both halves:

``` sql
-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';
ALTER TABLE py_api_notes ADD COLUMN IF NOT EXISTS title text;

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
-- squawk-ignore ban-drop-column
ALTER TABLE py_api_notes DROP COLUMN IF EXISTS title;
```

- **Every name under the file's prefix:** tables,
  views, functions, procedures, indexes, sequences,
  types, triggers. `make check` refuses a file whose
  objects are not `py_api_*`, or whose name carries no
  service's prefix
- **`lock_timeout`:** a change that waits for a lock
  gives up after two seconds, rather than queueing
  every request behind it
- **`statement_timeout`:** a change that runs long is
  stopped, rather than holding its lock for minutes
- **`IF NOT EXISTS` and `IF EXISTS`:** a migration that
  failed part way can run again
- **One change a file.** dbmate runs each file in a
  transaction, so a file is applied whole or not at all

## 3 Lint It

Squawk reads every migration for what locks, rewrites
or breaks a live table. Expect `Found 0 issues`:

``` sh
make db-lint
```

A warning names its rule and links its page. Mend the
migration; if the statement is meant, as a drop in a
down is, put `-- squawk-ignore <rule>` on the line
above it.

## 4 Apply It

With the stack up, expect `Applied:` and the file's
name:

``` sh
make db CMD=up
```

Then expect your migration among `[X]`, and
`Pending: 0`:

``` sh
make db CMD=status
```

`make dev` applies pending migrations too, at every
start.

## 5 Prove Its Down

Roll the newest back, then apply it again. Expect
`Rolled back:`, then `Applied:`, for the same file:

> [!CAUTION]
> A rollback runs the down: what it drops, the rows in
> it go with it. In the dev stack that is test data
> alone.

``` sh
make db CMD=rollback
```

``` sh
make db CMD=up
```

The down is for your machine and for a mistake caught
before release. Once a migration has run anywhere that
matters, the way back is a new migration forward.

## 6 Commit It with Its Schema

Write the schema the migrations make to
`migrations/schema.sql`. Expect
`Writing: /work/schema.sql`:

``` sh
make db CMD=dump
```

Commit the migration, `schema.sql` and the code that
uses the change, together, in one pull request.
`schema.sql` is the schema to read; the migrations are
how it was made.

## 7 Release It

A tag `vX.Y.Z` whose changes include `migrations/`
builds the migrations image and records its digest:
[How a release reaches the
box](../onboarding/ci-cd.md). The box runs it before
any service starts, so the new schema is there before
the code that needs it.

## 8 Change a Live Table Without Locking It

  ---------------------------------------------------------
  To                  Do
  ------------------- -------------------------------------
  Add a column        Nullable, or with a constant default:
                      no rewrite of the table

  Make a column       `CHECK (col IS NOT NULL) NOT VALID`
  required            in one migration;
                      `VALIDATE CONSTRAINT` in the next

  Limit a value       A `CHECK ... NOT VALID`, then
                      `VALIDATE`, as above

  Index a column      `CREATE INDEX CONCURRENTLY`, alone in
                      its file, `transaction:false`

  Rename a column     Add the new, write both, backfill,
                      read the new, then drop the old: one
                      release each

  Drop a column       Once no released code reads it

  Change an accessor  A new function beside the old; the
                      old dropped once no released code
                      calls it
  ---------------------------------------------------------

`VALIDATE` reads every row, but blocks only other
schema changes, not reads or writes; give its migration
a longer `statement_timeout`.

A concurrent index cannot run in a transaction, and
PostgreSQL runs statements sent together as one,
whatever dbmate is told. So its file holds the one
statement, with no `SET`, and says why to Squawk:

``` sql
-- migrate:up transaction:false
-- squawk-ignore ban-concurrent-index-creation-in-transaction, require-lock-timeout, require-statement-timeout
CREATE INDEX CONCURRENTLY IF NOT EXISTS py_api_notes_created_idx ON py_api_notes (created_at);

-- migrate:down transaction:false
-- squawk-ignore ban-concurrent-index-creation-in-transaction, require-lock-timeout, require-statement-timeout
DROP INDEX CONCURRENTLY IF EXISTS py_api_notes_created_idx;
```

## 9 The Rules

- **Never edit a migration once it has run anywhere but
  your machine.** dbmate records only that a file ran,
  not what it said; an edit is never applied where it
  already ran. Write a new one

- **The code runs on the schema before and after.**
  Migrations run before the new code starts, and the
  old code may meet the new schema for a moment. Add
  first, use in a later release, remove last

- **A service checks its schema at start.** It refuses
  to run when the newest version in `schema_migrations`
  is older than the one its code needs:

  ``` sql
  SELECT max(version) FROM schema_migrations;
  ```

  So a release in the wrong order fails loudly, not
  quietly wrong

- **Names and accessors:** [the database's
  conduct](../conduct/database.md)

## 10 Without Docker

PostgreSQL in your own directory, and dbmate's single
binary, need no root ([the local stack's
page](../onboarding/local-dev.md), §11). With the
database and logins made by `dev/out/db-users.sql`,
from `python3 box/render.py --dev`, run dbmate as the
migrator. Expect `Applied:`, and `schema.sql` written:

``` sh
DATABASE_URL='postgres://example_migrator:dev-only@127.0.0.1:55432/example?sslmode=disable'
dbmate --url "${DATABASE_URL}" -d migrations/sql -s migrations/schema.sql up
```

dbmate's `dump` needs `pg_dump` on your `PATH`, of
PostgreSQL's version or later.

## 11 What Can Go Wrong

- **`make check`: `TABLE notes is not py_api_*`.** An
  object without its file's prefix. Rename it; nothing
  has run yet
- **`CREATE INDEX CONCURRENTLY cannot run inside a transaction block (25001)`.**
  Another statement shares its file, a `SET` among
  them. Leave it alone in the file, as §8
- **`canceling statement due to lock timeout`.**
  Something held the table for two seconds. Nothing was
  changed; run it again, or find what holds the lock
- **`permission denied for schema public`.** The
  service's own login tried to change the schema. Only
  a migration may
- **A table or column the code expects is missing, and
  the migration shows `[X]`.** The file was edited
  after it ran. Write the change as a new migration
- **Squawk warns of a drop in a down.** Meant: put
  `-- squawk-ignore ban-drop-table`, `ban-drop-column`
  or `ban-drop-function` above it

## 12 See Also

- [The database](README.md): one database, its logins
  and its image
- [The database's conduct](../conduct/database.md):
  prefixes and accessors
- [dbmate](https://github.com/amacneil/dbmate) and
  [Squawk's rules](https://squawkhq.com/docs/rules),
  read 2026-10-06
