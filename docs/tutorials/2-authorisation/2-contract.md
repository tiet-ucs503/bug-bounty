---
abstract: |
  Step 2 of tutorial 2: what tutorials 4 to 7 may rely
  on, and nothing about how. Each accessor's signature,
  the permission it needs, what it answers, and how it
  refuses; the one function the users unit publishes;
  and the refusals as HTTP. Once written, the contract
  outranks the concept wherever both speak.
date: 2026-10-07
keywords:
- tutorial
- authz
- contract
- db
kind: reference
sources:
- migrations/sql/20261006120000_py_api_create_notes.sql
status: draft
subtitle: Step 2, what others may rely on
title: "2.2 What Each May Do: the Contract"
version: v0.1.0
---

## 1 Who Relies on It

- **Tutorials 4 and 5,** `/users` in a service: they
  call the users unit's accessors and turn their
  refusals into HTTP
- **Tutorial 6,** the dashboard: it shows what
  `users_me` answers
- **Tutorial 7,** uploads: py-api's objects ask
  `users_may`, as the notes do
- **Any unit you add later:** it asks `users_may`, and
  nothing else of the users unit

Each may be written against this page before the
implementation exists. Every accessor takes **the
caller first**, the `sub` from the token, and decides
for itself.

## 2 The Users Unit

- **`users_may(sub, permission)`**
  - Needs: nothing
  - Answers: `boolean`
  - Refuses: never
- **`users_me(sub)`**
  - Needs: nothing
  - Answers: a row: `sub`, `email`, `roles`,
    `permissions`; no row if never signed in
  - Refuses: never
- **`users_list(caller)`**
  - Needs: `users.read`
  - Answers: rows: `sub`, `email`, `roles`,
    `first_seen_at`, `seen_at`; by e-mail, at most 1000
  - Refuses: `42501`
- **`users_matrix(caller)`**
  - Needs: `users.read`
  - Answers: rows: `role`, `about`, `permissions`
  - Refuses: `42501`
- **`users_grant(caller, sub, role)`**
  - Needs: `users.grant`
  - Answers: nothing; twice is once
  - Refuses: `42501`; `P0002` for a person or a role
    that does not exist
- **`users_revoke(caller, sub, role)`**
  - Needs: `users.grant`
  - Answers: nothing
  - Refuses: `42501`; `P0002` if the person lacks the
    role; `23001` for the last `users.grant`
- **`users_may` is published.** It is the one function
  of the users unit that another unit may call; its
  comment says so, and [the database's
  conduct](../../conduct/database.md) holds every unit
  to it
- **`users_revoke` refuses `23001`** for the last
  `users.grant` there is, and for nothing else
- **Roles and permissions** come back as arrays, sorted
- **Starting roles are no accessor.** No service calls
  them: a trigger gives them when tutorial 1's
  `users_person_see` first records a person (R10)

## 3 py-api's Notes

- **`py_api_note_new(caller, body)`**
  - Needs: `notes.write`
  - Answers: the note's `id`; the caller owns it
  - Refuses: `42501`
- **`py_api_notes_all(caller, before, limit)`**
  - Needs: `notes.read`
  - Answers: rows: `id`, `body`, `mine`, `created_at`,
    `updated_at`; newest first
  - Refuses: `42501`
- **`py_api_note_edit(caller, id, body)`**
  - Needs: `notes.write`, and the owner
  - Answers: nothing
  - Refuses: `42501`; `P0002` if there is no such note
- **`py_api_note_drop(caller, id)`**
  - Needs: `notes.write`, and the owner
  - Answers: nothing
  - Refuses: `42501`; `P0002` if there is no such note
- **`py_api_notes_all` pages:** `before`, an `id`, for
  the next page, `NULL` for the first; `limit` 50 by
  default, at most 200
- **Never whose:** it answers `mine`, never an owner
- **Another's note is `42501`; no note is `P0002`.**
  Different answers, so a client can tell them apart
- **The template's `py_api_note_add` and
  `py_api_notes_of` are kept** as they are: their
  signatures were promised before this tutorial, and
  the new accessors sit beside them

## 4 The Refusals

Each accessor refuses with an SQLSTATE, which a service
turns into HTTP:

  -------------------------------------------------------
  SQLSTATE   Name                       HTTP   Means
  ---------- -------------------------- ------ ----------
  `42501`    `insufficient_privilege`   403    Not
                                               allowed

  `P0002`    `no_data_found`            404    No such
                                               thing

  `23001`    `restrict_violation`       409    Would
                                               break a
                                               rule of
                                               the data

  `23514`    `check_violation`          400    A value
                                               out of
                                               bounds
  -------------------------------------------------------

## 5 See Also

- [The tests](3-tests.md): next, held to this page, and
  [the implementation](4-implementation.md): after it
- [The cycle](../../conduct/the-cycle/README.md) §2:
  what a contract is for, and how it changes
