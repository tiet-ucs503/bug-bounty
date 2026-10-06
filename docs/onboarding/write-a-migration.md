---
abstract: |
  Change a service's database schema: write a migration
  with dbmate, lint it with Squawk, apply and roll it
  back in the dev stack, and commit it with the schema
  it makes. With the patterns that change a live table
  without locking it.
date: 2026-10-06
keywords:
- db
- migration
- dbmate
- squawk
- postgres
kind: how-to
sources:
- db/py-api/migrations/20261006120000_create_notes.sql
- .squawk.toml
- box/render.py
- Makefile
status: draft
subtitle: dbmate's plain SQL, Squawk's lint, one change
  at a time
title: Write a Migration
version: v0.1.0
---

## 1 Before You Start

- **The box has no database yet.** It moves to
  PostgreSQL first; until then a schema lives in the
  dev stack alone, and a service that needs one runs
  locally only. A migration written now runs on the box
  unchanged, the same way, once the box has its
  database
- **The service asks for a database:**
  `"database": true` for it in `box/project.json`, and
  the folder `db/<service>/migrations/`. `make check`
  refuses either without the other. In the template,
  `py-api` asks, with one example migration
- **The dev stack,** [A local stack that mirrors the
  box](local-dev.md); or PostgreSQL and dbmate without
  Docker, §10
- **Node,** for Squawk, which npm fetches

## 2 How a Migration Runs

Each service with a database owns one, with two logins
of its own:

- **`<service>_migrator`:** owns the schema, and runs
  the migrations
- **`<service>`:** the service's own login, holding
  rows alone: `SELECT`, `INSERT`, `UPDATE`, `DELETE`,
  on every table the migrator makes, by default
  privileges. It cannot create, alter or drop

`py-api`'s are `py_api_migrator` and `py_api`, in the
database `py_api`: PostgreSQL's names take no hyphen.

``` mermaid
---
config:
  themeVariables:
    edgeLabelBackground: "#d9eaf2"
  themeCSS: ".edgeLabel, .edgeLabel p, .labelBkg { background-color: #d9eaf2 !important; color: #5c7a8a !important; }"
---
flowchart LR
  users["db-users<br/>the database, two logins"]
  migrate["migrate-py-api<br/>dbmate up, as the migrator"]
  svc["py-api<br/>rows alone, as py_api"]
  db[("PostgreSQL<br/>py_api")]
  users -->|"then"| migrate
  migrate -->|"then"| svc
  users --> db
  migrate -->|"schema_migrations"| db
  svc -->|"DATABASE_URL"| db
  classDef compute fill:#fff6eb,stroke:#804900,color:#804900
  class users,migrate,svc compute
  classDef storage fill:#dcfce7,stroke:#22c55e,color:#111
  class db storage
```

At every start of the stack, `migrate-<service>`
applies every migration not yet in the database's
ledger, `schema_migrations`, in the order of their
names, and the service starts only if all of them
succeed. A broken migration stops its own service and
no other.

## 3 Write One

A file named by the time it is made, with its up and
its down. Expect the new file's path:

``` sh
make db-new SVC=py-api NAME=notes_add_title
```

Write the change under `-- migrate:up`, and its undoing
under `-- migrate:down`. Keep the two `SET` lines the
file starts with, in both halves:

``` sql
-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';
ALTER TABLE notes ADD COLUMN IF NOT EXISTS title text;

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
-- squawk-ignore ban-drop-column
ALTER TABLE notes DROP COLUMN IF EXISTS title;
```

- **`lock_timeout`:** a change that waits for a lock
  gives up after two seconds, rather than queueing
  every request behind it
- **`statement_timeout`:** a change that runs long is
  stopped, rather than holding its lock for minutes
- **`IF NOT EXISTS` and `IF EXISTS`:** a migration that
  failed part way can run again
- **One change a file.** dbmate runs each file in a
  transaction, so a file is applied whole or not at all

## 4 Lint It

Squawk reads every migration for what locks, rewrites
or breaks a live table. Expect `Found 0 issues`:

``` sh
make db-lint
```

A warning names its rule and links its page. Mend the
migration; if the statement is meant, as a drop in a
down is, put `-- squawk-ignore <rule>` on the line
above it.

## 5 Apply It

With the stack up, expect `Applied:` and the file's
name:

``` sh
make db SVC=py-api CMD=up
```

Then expect your migration among `[X]`, and
`Pending: 0`:

``` sh
make db SVC=py-api CMD=status
```

`make dev` applies pending migrations too, at every
start.

## 6 Prove Its Down

Roll the newest back, then apply it again. Expect
`Rolled back:`, then `Applied:`, for the same file:

> [!CAUTION]
> A rollback runs the down: what it drops, the rows in
> it go with it. In the dev stack that is test data
> alone.

``` sh
make db SVC=py-api CMD=rollback
```

``` sh
make db SVC=py-api CMD=up
```

The down is for your machine and for a mistake caught
before release. Once a migration has run anywhere that
matters, the way back is a new migration forward.

## 7 Commit It with Its Schema

Write the schema the migrations make to
`db/py-api/schema.sql`. Expect
`Writing: /db/schema.sql`:

``` sh
make db SVC=py-api CMD=dump
```

Commit the migration, `schema.sql` and the code that
uses the change, together. `schema.sql` is the schema
to read; the migrations are how it was made.

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
CREATE INDEX CONCURRENTLY IF NOT EXISTS notes_owner_idx ON notes (owner);

-- migrate:down transaction:false
-- squawk-ignore ban-concurrent-index-creation-in-transaction, require-lock-timeout, require-statement-timeout
DROP INDEX CONCURRENTLY IF EXISTS notes_owner_idx;
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

  So a deploy in the wrong order fails loudly, not
  quietly wrong

- **One database per service.** A service never reads
  another's; it calls the other service

## 10 Without Docker

PostgreSQL in your own directory, and dbmate's single
binary, need no root (see [the local stack's
page](local-dev.md), §11). With the database and logins
made by `dev/out/db-users.sql`, from
`python3 box/render.py --dev`, run dbmate as the
migrator. Expect `Applied:`, and `schema.sql` written:

``` sh
DATABASE_URL='postgres://py_api_migrator:dev-only@127.0.0.1:55432/py_api?sslmode=disable'
dbmate --url "${DATABASE_URL}" -d db/py-api/migrations -s db/py-api/schema.sql up
```

dbmate's `dump` needs `pg_dump` on your `PATH`, of
PostgreSQL's version or later.

## 11 What Can Go Wrong

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
  `-- squawk-ignore ban-drop-table` or
  `ban-drop-column` above it

## 12 See Also

- [A local stack that mirrors the box](local-dev.md):
  the stack the migrations run in
- [The manifest, key by key](manifest.md): `database`
- [dbmate](https://github.com/amacneil/dbmate) and
  [Squawk's rules](https://squawkhq.com/docs/rules),
  read 2026-10-06
