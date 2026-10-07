---
abstract: |
  Step 5 of tutorial 3: run the tests against the
  migrations, read what they say, and change whichever
  step is wrong. How to read a result, how to try the
  tests by breaking a migration on purpose, and a
  refinement of tutorial 2's tests made while this
  tutorial was written.
date: 2026-10-07
keywords:
- tutorial
- db
- migration
- tests
- cycle
kind: how-to
sources:
- migrations/sql/20261006120000_py_api_begin.sql
status: draft
subtitle: Step 5, run, read, refine
title: "3.5 Make It a Migration: the Refinement"
version: v0.1.0
---

## 1 Run

Expect eight lines starting `ok`, then `8 of 8 pass`.
The run applies whatever is pending, rolls tutorial 3's
three back, and applies them again:

``` sh
./test-3.sh
```

Its exit status is 0 when all pass, and 3 when any
fails.

## 2 Read the Result

What a test got says where to look:

- **T3.1 `got no`:** `box/project.json` does not give
  `users` to a service yet
- **T3.2 with fewer than `7 2 12 1`:** a migration is
  missing a piece of its draft, or did not apply. Its
  `Applied:` line, or its error, is in `make db CMD=up`
- **`42883` or `42P01`:** a function or a table is not
  there: the migration that makes it has not run
- **T3.5 short of 27:** a migration differs from its
  draft. Run `test-2.sql` alone on the migrations, and
  read [tutorial 2's
  refinement](../2-authorisation/5-refinement.md) §3
- **T3.7 with a name in it:** the newest three
  migrations are not tutorial 3's, so nothing was
  rolled back. Later migrations, such as tutorial 7's,
  sit on top of them
- **T3.7 above `0`:** a down leaves something behind.
  The count says how many

**Read the first failure first.** A migration that did
not apply fails every test after it.

## 3 Try the Tests Themselves

Break a migration on purpose, in a copy, and check that
a test fails. Here, take the trigger's function out of
the roles' down, so a rollback leaves it behind. Roll
the three back first, so the broken down is the one
that runs. Expect `FAIL` for T3.7, and `7 of 8 pass`:

``` sh
for i in 1 2 3; do make db CMD=rollback; done
cp migrations/sql/*_users_create_roles.sql /tmp/roles.sql
sed -i '/DROP FUNCTION IF EXISTS users_person_start();/d' migrations/sql/*_users_create_roles.sql
./test-3.sh
```

Then put it back, and clean up after the broken down:

``` sh
for i in 1 2 3; do make db CMD=rollback; done
cp /tmp/roles.sql migrations/sql/*_users_create_roles.sql
psql "${MIGRATOR_URL}" -c "DROP FUNCTION IF EXISTS users_person_start()"
make db CMD=up
```

On the native stack, `dbmate` as in [the
implementation](4-implementation.md) §6, for `make db`.

## 4 What to Refine

A failure says something is wrong; it does not say
what:

- **A test fails, and the concept and contract are
  right:** the migrations
- **A broken migration passes every test:** the tests
- **The migrations are right, and a test wants
  something else:** the test, or the rule it came from
- **Tutorial 4 needs a function the contract lacks:**
  the contract, then the tests, then a new migration

## 5 A Refinement of Tutorial 2's Tests

The first run of T3.5 failed. Tutorial 2's tests make
"you" the first admin by hand, with a plain `INSERT`.
On the migrations, the first-admin migration had
already made "you" an admin at the first sign-in, so
the `INSERT` broke the key, `23505`, and the tests
stopped.

The migrations were right: R7 says the first admin is
made at the first sign-in. The test's setup assumed
nobody else would make them. So tutorial 2's tests were
refined, not the migrations: the `INSERT` now ends
`ON CONFLICT DO NOTHING`, and is the same on the drafts
and on the migrations. A refinement may reach back into
an earlier tutorial, when that tutorial's step is the
one that is wrong.

## 6 What Can Go Wrong

- **`make check`:
  `not <14-digit version>_<prefix>_<what>.sql`.**
  `users` is not among a service's `prefixes` yet; or
  the file was named by hand
- **`function users_permission_add(...) does not exist`,
  applying a later unit's migration.** Its file sorts
  before the roles'. Rename it with a later time;
  nothing has run anywhere else yet
- **`permission denied for table schema_migrations`, as
  the services' login.** As meant: only the migrator
  writes dbmate's ledger
- **A table you expect is missing, and the migration
  shows `[X]`.** It was edited after it ran. Write a
  new one

## 7 See Also

- [4 /users](../4-users/README.md): next
- [The cycle](../../conduct/the-cycle/README.md) §3:
  what to refine, in general
