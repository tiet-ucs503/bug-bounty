---
abstract: |
  Step 2 of tutorial 2: what tutorials 3 to 7 may rely
  on, and nothing about how. Each accessor's signature,
  the permission it needs, what it answers, and how it
  refuses; the three functions the users unit
  publishes, one to ask and two for a unit's
  migrations; and the refusals as HTTP. Once written,
  the contract outranks the concept wherever both
  speak.
date: 2026-10-07
keywords:
- tutorial
- authz
- contract
- db
kind: reference
sources:
- tools/native-dev.sh
status: draft
subtitle: Step 2, what others may rely on
title: "2.2 What Each May Do: the Contract"
version: v0.1.0
---

## 1 Who Relies on It

- **Tutorial 3,** the migrations, which carry these
  accessors as they are
- **Tutorial 4,** `/users` in a service: it calls the
  users unit's accessors and turns their refusals into
  HTTP
- **Tutorial 5,** the notes: their migration brings
  `notes.read` and `notes.write`, and every accessor of
  theirs asks `users_may`
- **Tutorial 6,** the dashboard: it shows what
  `users_me` answers
- **Tutorial 7,** uploads: its migration brings
  `objects.write`, and py-api's objects ask `users_may`
- **Any unit you add later:** the same three published
  functions, and nothing else of the users unit

Each may be written against this page before the
implementation exists. Every accessor takes **the
caller first**, the `sub` from the token, and decides
for itself.

## 2 The Users Unit

- **`users_may(sub, permission)`** : *Whether Bhanu or
  Chitra holds a permission, such as `example.write`.*
  - Needs: nothing
  - Answers: `boolean`
  - Refuses: never
- **`users_me(sub)`** : *GET my `sub`, `email`, `roles`
  and `permissions`.*
  - Needs: nothing
  - Answers: a row: `sub`, `email`, `roles`,
    `permissions`; no row if never signed in
  - Refuses: never
- **`users_list(caller)`** : *GET the list of `users`.*
  - Needs: `users.read`
  - Answers: rows: `sub`, `email`, `roles`,
    `first_seen_at`, `seen_at`; by e-mail, at most 1000
  - Refuses: `42501`
- **`users_matrix(caller)`** : *GET the access control
  `matrix`.*
  - Needs: `users.read`
  - Answers: rows: `role`, `about`, `permissions`
  - Refuses: `42501`
- **`users_grant(caller, sub, role)`** : *GRANT a ROLE
  to a USER.*
  - Needs: `users.grant`
  - Answers: nothing; twice is once
  - Refuses: `42501`; `P0002` for a person or a role
    that does not exist
- **`users_revoke(caller, sub, role)`** : *REVOKE a
  ROLE from a USER.*
  - Needs: `users.grant`
  - Answers: nothing
  - Refuses: `42501`; `P0002` if the person lacks the
    role; `23001` for the last `users.grant`
- **`users_permission_add(permission, about,
  roles)`** : *ADD a PERMISSION (along with ROLES) into
  the MATRIX.*
  - Called by: a unit's migration, on its way up
  - Answers: nothing; twice is once. The permission,
    and a cell for each role named; `roles` may be
    empty
  - Refuses: `P0002` for a role that does not exist;
    `23514` for a name not `<unit>.<verb>`
- **`users_permission_drop(permission)`** : *DROP a
  PERMISSION from the MATRIX.*
  - Called by: a unit's migration, on its way down
  - Answers: nothing; twice is once. The permission
    gone, and every cell of it
  - Refuses: `42501` for a `users.` permission
- **Three functions are published:** `users_may`, for
  any unit's accessors, and the two above, for any
  unit's migrations. They are the only functions of the
  users unit that another unit may call; their comments
  say so, and [the database's
  conduct](../../conduct/database.md) holds every unit
  to them
- **The two for migrations take no caller.** A
  migration runs for the project, not for a person
- **`users_revoke` refuses `23001`** for the last
  `users.grant` there is, and for nothing else
- **Roles and permissions** come back as arrays, sorted
- **Starting roles are no accessor.** No service calls
  them: a trigger gives them when tutorial 1's
  `users_person_see` first records a person (R10)

## 3 The Refusals

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

## 4 See Also

- [The tests](3-tests.md): next, held to this page, and
  [the implementation](4-implementation.md): after it
- [The cycle](../../conduct/the-cycle/README.md) §2:
  what a contract is for, and how it changes
