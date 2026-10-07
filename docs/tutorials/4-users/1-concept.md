---
abstract: |
  Step 1 of tutorial 4: what `/users` is for. The goal,
  eight rules, and what it will not do.
date: 2026-10-07
keywords:
- tutorial
- auth
- authz
- concept
kind: explanation
sources:
- services/py-api/main.py
- services/js-api/server.js
status: draft
subtitle: Step 1, what and why
title: "4.1 /users: the Concept"
version: v0.1.0
---

> [!NOTE]
> This concept is subject to refinement during the
> development process. Until [the
> contract](2-contract.md) exists, and wherever it is
> silent, this page is the source of truth.

## 1 The Goal

**Tutorials 1 and 2's database, over HTTP, for the UI
and anything else that signs in.** The service checks
who is calling; the database decides what they may do.
The service adds the few things only it can: the token,
Cognito's `userInfo`, and turning a refusal into HTTP.

## 2 Where It Lives

`/users` is a part of the service you take, not a
service of its own: the same host, `py-api.<zone>` or
`js-api.<zone>`, the same image and the same process,
its routes under `/users`. Tutorial 3 gave that service
the `users` prefix beside its own.

## 3 The Rules

- **U1 No token, no answer.** Every `/users` route
  needs the pool's access token, issued to your UI or
  the box's probes, unexpired: `401` otherwise
- **U2 `/users/me` is where a person is first seen.**
  It asks `userInfo` for the e-mail, and records the
  person by `users_person_see`, with the provider from
  the token's `username`. An unverified e-mail is not
  kept: `403`
- **U3 `/users/me` answers who you are:** your `sub`,
  e-mail, provider, profile, roles and permissions.
  Signed in with no role, you are recorded, and may do
  nothing
- **U4 Your profile is yours.** `PUT /users/me/profile`
  changes the caller's own, and nobody else's
- **U5 The database decides.** Each route calls one
  accessor, the caller first; the service checks no
  permission itself. A refusal becomes HTTP by its
  SQLSTATE: `42501` 403, `P0002` 404, `23001` 409,
  `23514` 400
- **U6 nginx passes the manifest's routes, and only
  those**
- **U7 Two languages, one contract.** py-api and js-api
  answer the same requests the same way, so one set of
  tests holds both
- **U8 Never cached.** Every answer is the caller's
  own: `Cache-Control: no-store`

## 4 What It Will Not Do

- **Sign anyone in.** The box's Cognito does; the UI
  starts it (tutorial 6)
- **Let an admin change someone else's profile.** That
  would be a permission, `users.edit`, and a row in the
  matrix: a turn of the cycle for when a project needs
  it
- **Serve the notes.** They are py-api's own routes,
  tutorial 6's

## 5 See Also

- [The contract](2-contract.md): next, then [the
  tests](3-tests.md)
- [How the project meets the
  box](../../onboarding/README.md) §3 and §4: what
  nginx decides, and what your service does
