---
abstract: |
  Step 2 of tutorial 3: what the migrations promise.
  Their files and order, the manifest's prefix, every
  function the users unit offers, what a rollback does,
  and where the first admin's address goes.
date: 2026-10-07
keywords:
- tutorial
- db
- migration
- contract
kind: reference
sources:
- migrations/sql/20261006120000_py_api_begin.sql
- box/project.json
status: draft
subtitle: Step 2, what others may rely on
title: "3.2 Make It a Migration: the Contract"
version: v0.1.0
---

## 1 Who Relies on It

- **Tutorial 4,** `/users` in a service: it calls the
  users unit's functions, and needs its prefix
- **Tutorials 5 and 7,** the notes and uploads: their
  migrations come after these, bring their permissions
  by `users_permission_add`, and their accessors ask
  `users_may`
- **The box's owner,** who reads every migration before
  the box runs it

## 2 The Files, in Order

Three files in `migrations/sql/`, after the template's
own `py_api_begin`, each named
`<version>_<prefix>_<what>.sql`. `make db-new` stamps
the version with the time, so files made in this order
run in this order:

1.  `<version>_users_create_people.sql`
2.  `<version>_users_create_roles.sql`
3.  `<version>_users_first_admin.sql`

Each holds `-- migrate:up` and `-- migrate:down`, and
both begin with the two `SET` lines `make db-new`
writes.

## 3 The Manifest

The service that serves `/users` owns the `users`
prefix after its own. For py-api, in
`box/project.json`:

``` json
"prefixes": ["py_api", "users"],
```

For js-api, `["js_api", "users"]`. One service owns
`users`, never two.

## 4 What the Users Unit Offers

Tutorial 1's functions:

- **`users_person_see(sub, email, verified, provider)`**
  - Needs: nothing; the service calls it at sign-in
  - Answers: `true` if the person is recorded; `false`,
    and nothing kept, if the e-mail is not verified
  - Refuses: never
- **`users_profile_get(sub)`**
  - Needs: nothing
  - Answers: a row: `sub`, `email`, `provider`,
    `display_name`, `affiliation`; no row if never
    recorded
  - Refuses: never
- **`users_profile_set(sub, display_name, affiliation)`**
  - Needs: nothing; the service passes the caller's own
    `sub`
  - Answers: nothing
  - Refuses: `P0002` if the person was never recorded;
    `23514` for a value too long

Tutorial 2's, as [its
contract](../2-authorisation/2-contract.md) §2 gives
them: `users_may`, `users_me`, `users_list`,
`users_matrix`, `users_grant`, `users_revoke`,
`users_permission_add` and `users_permission_drop`.
Three are published, and their comments say so:
`users_may`, and the two a unit's migration calls.

The starting role is no function a service calls: a
trigger on `users_people` gives it, when
`users_person_see` first records a person.

## 5 What a Rollback Does

- Each down drops exactly what its up made, in the
  reverse order
- All three rolled back, the schema is the template's
  again
- **The rows go too:** every person and role the three
  made, and every permission a later unit brought. Roll
  back the later units first, as dbmate does, newest
  first

## 6 The First Admin

One address, in the third migration alone: a starting
role at position 1, before every other, giving `admin`.
If that person has signed in already, the migration
makes them `admin` at once.

## 7 See Also

- [The tests](3-tests.md): next, held to this page
- [The cycle](../../conduct/the-cycle/README.md) §2:
  what a contract is for, and how it changes
