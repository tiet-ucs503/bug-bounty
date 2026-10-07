---
abstract: |
  Step 5 of tutorial 2: run the tests against the
  drafts, read what they say, and change whichever step
  is wrong. The setup, the run, how to read a result,
  how to try the tests themselves by breaking the code
  on purpose, and a refinement of the tests made while
  this tutorial was written. Refinement may change the
  concept, the contract and the tests, not only the
  code.
date: 2026-10-07
keywords:
- tutorial
- authz
- tests
- cycle
kind: how-to
sources:
- migrations/sql/20261006120000_py_api_create_notes.sql
status: draft
subtitle: Step 5, run, read, refine
title: "2.5 What Each May Do: the Refinement"
version: v0.1.0
---

## 1 The Setup

- **The database:** your local stack's, with only the
  template's migration applied. Tutorials 1 and 2 are
  drafts, not migrations, until tutorial 3
- **The files,** at your fork's root, in this order:
  `users-draft.sql`, then `notes-draft.sql`, whose
  functions call `users_may`, then `test-2.sql`
- **One transaction, rolled back.** The drafts and the
  tests run inside `BEGIN` and `ROLLBACK`, so every run
  starts from the same database and leaves it as it
  was. Nothing to clean up, and no run can spoil the
  next
- **The framework is the file itself.** `expect` runs
  each test in a savepoint; no tool to install

## 2 Run

Expect `t|t|t`, then 24 lines starting `ok`, then
`24 of 24 pass`:

``` sh
psql "${MIGRATOR_URL}" -X -q -t -A -v ON_ERROR_STOP=1 -c BEGIN -f users-draft.sql -f notes-draft.sql -f test-2.sql -c ROLLBACK
```

Its exit status is 0 when all pass, and 3 when any
fails, so a script or CI can run it as it is.

## 3 Read the Result

Each line is a test: `ok` or `FAIL`, its ID, what it
wants, and what it got. What it got says where to look:

  ----------------------------------------------------
  Got           Means
  ------------- --------------------------------------
  `42883`       A function is not there: a piece of
                [the
                implementation](4-implementation.md)
                not yet added, or added under another
                signature than [the
                contract](3-contract.md)'s

  `42P01`       A table is not there: the same, for a
                table

  Another       The accessor refused for the wrong
  SQLSTATE      reason, or refused when it should have
                answered

  An empty      The accessor answered when it should
  value         have refused: a check missing

  `nothing`     No row came back: the thing was gone,
                or never there

  A wrong value The rule is implemented, but not as
                [the concept](1-concept.md) says
  ----------------------------------------------------

**Read the first failure first.** A test that should
have refused, and did not, changes the data, and the
tests after it fail because of it, not on their own
account. A fix to the first often clears the rest.

## 4 Try the Tests Themselves

A test suite can be wrong too: it can pass code that
breaks a rule. Find out by breaking the code on
purpose, in a copy, and checking that some test fails.
Here, take out the owner from the notes' `WHERE`, so
anyone with `notes.write` may change any note. Expect
`FAIL` for T2.19, T2.20 and T2.22, and `21 of 24 pass`:

``` sh
sed 's/WHERE id = p_id AND owner = p_caller;/WHERE id = p_id;/' notes-draft.sql > broken.sql
psql "${MIGRATOR_URL}" -X -q -t -A -v ON_ERROR_STOP=1 -c BEGIN -f users-draft.sql -f broken.sql -f test-2.sql -c ROLLBACK
rm broken.sql
```

If every test passes with the code broken, the tests
are what needs refining.

## 5 What to Refine

A failure says something is wrong; it does not say
what. **Refinement may change any step, not only the
code:**

  ----------------------------------------------------
  You see                         Refine
  ------------------------------- --------------------
  A test fails, and the concept   The implementation
  and contract are right          

  Broken code passes every test   The tests

  The code is right, and a test   The test, or the
  wants something else            concept it came from

  A signature the next tutorial   The contract, then
  cannot use                      the tests and the
                                  code

  A rule nobody can test          The concept
  ----------------------------------------------------

Then run again. A turn ends when every test passes and
nothing in the concept, the contract or the tests wants
changing.

## 6 A Refinement of the Tests

While this tutorial was written, its tests numbered 23,
and had one test for R5: T2.12, the last `users.grant`
refused. §4's way of trying them found the gap. A
`users_revoke` that refused **every** revoke, not just
the last, passed all 23: T2.12 asked for a refusal, and
got one.

The code was right; the tests could not tell it from
wrong code. So the tests were refined, not the code:
T2.13 was added: any other `users.grant`, taken away,
is gone. It checks the second half of R5 in [the
concept](1-concept.md), "any other can", which T2.12
had left untested. The tests after it moved up by one.

The same broken `users_revoke` now fails T2.13, and
passes 23 of 24.

## 7 What Can Go Wrong

- **`function users_may(text, text) does not exist`,
  and `psql` stops.** `notes-draft.sql` ran before
  `users-draft.sql`. A function in `LANGUAGE sql` is
  checked when it is made; give the files in order
- **Every check fails for someone you granted.** The
  role has no row in `users_grants` for that
  permission:
  `SELECT * FROM users_grants WHERE role = 'member'`
- **A permission's name is refused by a `CHECK`.** It
  must be `<unit>.<verb>`, lower case, one dot
- **You want "everyone but bhanu".** A matrix cannot
  say no ([the concept](1-concept.md) §5). Take bhanu's
  role, or give the others a role he lacks
- **`relation "t2_results" already exists`.** The tests
  ran twice in one session without a rollback. Run them
  as §2 does, between `BEGIN` and `ROLLBACK`

## 8 See Also

- [3 Make it a migration](../3-the-migration.md): next,
  the drafts as migrations, as they are
- [The cycle](../../conduct/the-cycle/README.md) §3:
  what to refine, in general
