---
abstract: |
  Step 5 of tutorial 5: run the tests, read what they
  say, and change whichever step is wrong. How to read
  a result, how to try the tests themselves by breaking
  the migration on purpose, and two refinements made
  while this tutorial was written: one to its tests,
  and one that moved the notes out of tutorial 2.
date: 2026-10-07
keywords:
- tutorial
- notes
- tests
- cycle
kind: how-to
sources:
- tools/native-dev.sh
status: draft
subtitle: Step 5, run, read, refine
title: "5.5 Notes: the Refinement"
version: v0.1.0
---

## 1 Run

Expect eighteen lines starting `ok`, then
`18 of 18 pass`:

``` sh
./test-5.sh
```

Its exit status is 0 when all pass, and 3 when any
fails. The database's twelve are rolled back; the six
through nginx delete the note they add and take back
the roles they give.

## 2 Read the Result

What a test got says where to look:

- **`42883` or `42P01` in T5.1 to T5.12:** a function
  or the table is not there: the migration has not run,
  or ran under another name. `make db CMD=status`
- **T5.1 `got false`, T5.2 `got nothing`:** the
  permissions were not brought, or not to those roles:
  `SELECT * FROM users_grants WHERE permission LIKE 'notes.%'`
- **An empty value where a refusal was wanted:** an
  accessor acted without asking, or without the owner
  in its `WHERE`
- **`404` through nginx:** the manifest lacks the
  route, or the stack was not restarted after it
  changed
- **`403` for T5.13 and T5.14:** asha holds no
  `notes.write`. The roles are given through `/users`,
  so read `test-5.sh`'s first lines' answers

**Read the first failure first.** A note that was not
written fails every test after it that reads it.

## 3 Try the Tests Themselves

Break the migration on purpose, in a copy, and check
that a test fails. Here, take the owner out of edit's
and delete's `WHERE`, so anyone with `notes.write` may
change any note. Roll the notes back first, so the
broken migration is the one that runs.

> [!CAUTION]
> Rolling the notes back drops their table: every note
> on your local stack goes with it.

Expect `FAIL` for T5.8, T5.9 and T5.17, and
`15 of 18 pass`:

``` sh
make db CMD=rollback
cp migrations/sql/*_py_api_create_notes.sql /tmp/notes.sql
sed -i 's/WHERE id = p_id AND owner = p_caller;/WHERE id = p_id;/' migrations/sql/*_py_api_create_notes.sql
make db CMD=up
./test-5.sh
```

Then put it back:

``` sh
make db CMD=rollback
cp /tmp/notes.sql migrations/sql/*_py_api_create_notes.sql
make db CMD=up
```

On the native stack, `dbmate` as in [the
implementation](4-implementation.md) §3, for `make db`.
If every test passes with the migration broken, the
tests are what needs refining.

## 4 What to Refine

A failure says something is wrong; it does not say
what:

- **A test fails, and the concept and contract are
  right:** the migration, or the routes
- **A broken migration passes every test:** the tests
- **The code is right, and a test wants something
  else:** the test, or the rule it came from
- **Tutorial 6 needs something the contract lacks:**
  the contract, then the tests, then a new migration

## 5 A Refinement of the Tests

The first run on a fresh stack failed T5.13, T5.14,
T5.15 and T5.17, each with `403`. The tests gave asha
and bhanu their roles through `/users`, as you, the
first admin; but on that stack you had never signed in.
Your starting role is given at your first sign-in
(tutorial 2's R10), so you held no role, and every
grant was refused.

The code was right. The tests had leant on tutorial 4's
tests having signed you in first, on the same stack. So
the tests were refined, not the code: `test-5.sh` now
calls `/users/me` as you before anything else, and runs
the same on a stack of its own.

## 6 A Refinement of the Concept, Across Tutorials

The notes began in tutorial 2. Its matrix had the
notes' columns, its rules R7 and R8 were the notes'
rules, and its tests wrote notes. It worked, and every
test passed. But the users unit could not be built,
tested or reused without notes, and nothing showed how
a later unit should join the matrix.

The concept was refined, and the change ran through
four tutorials:

- **Tutorial 2** lost the notes. Its matrix starts with
  the users unit's own two columns, and its contract
  gained the two published functions a unit's migration
  calls, `users_permission_add` and
  `users_permission_drop`; an `example` unit stands in
  for the notes in its tests
- **Tutorial 3** carries three migrations, not four
- **This tutorial** is new: the notes as a unit of
  their own, joining the matrix by the published door
- **The template's** starter migration, a notes table
  with no rules, was emptied, so a fork no longer
  starts with notes nobody may use

A refinement may reach across tutorials when the step
that is wrong is an early one. It is a turn of the
cycle like any other: the concept first, then the
contract, the tests and the code, in that order.

## 7 What Can Go Wrong

- **`function users_permission_add(text, text, text[]) does not exist`,
  applying the notes.** Tutorial 3's migrations have
  not run, or the notes' file sorts before the roles'.
  Rename it with a later time; nothing has run anywhere
  else yet
- **`P0002`, `no such role`, applying the notes.** The
  project has renamed or dropped `reader` or `member`.
  Name its own roles in the migration
- **`422` for every note.** The body is sent as a form,
  not JSON: `Content-Type: application/json`
- **A rollback refused, `42501`.** The down names a
  `users.` permission; the notes' are `notes.`

## 8 See Also

- [6 A Svelte UI](../6-a-svelte-ui/README.md): next, a
  page over the notes and `/users`
- [Bring an existing unit under
  authorisation](../../migrations/bring-under-authorisation.md):
  the same, for a unit that was there first
- [The cycle](../../conduct/the-cycle/README.md) §3:
  what to refine, in general
