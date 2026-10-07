---
abstract: |
  Step 2 of tutorial 4: what the UI and any other
  client may rely on. Each route, what it takes, what
  it answers, and how it refuses; the routes for the
  manifest.
date: 2026-10-07
keywords:
- tutorial
- api
- routes
- contract
kind: reference
sources:
- services/py-api/main.py
- services/js-api/server.js
- box/project.json
status: draft
subtitle: Step 2, what others may rely on
title: "4.2 /users: the Contract"
version: v0.1.0
---

## 1 Who Relies on It

- **Tutorial 5's UI,** which signs in, calls
  `/users/me`, shows the profile, and lets an admin
  give roles
- **Anything else with a token,** such as the box's
  probes

## 2 Every Route

All under `https://<service>.<zone>/users`, each with
`Authorization: Bearer <access token>`. Every answer is
JSON, with `Cache-Control: no-store`.

- **`GET /users/me`**
  - Needs: a verified e-mail
  - Answers: `200`,
    `{sub, email, provider, profile: {display_name, affiliation}, roles, permissions}`
  - Refuses: `403` `e-mail not verified`; `503` if
    `userInfo` or the database does not answer
- **`PUT /users/me/profile`**
  - Takes: `{display_name, affiliation}`, both text; a
    missing one is set empty
  - Answers: `200`, as `GET /users/me`
  - Refuses: `400` for a value that is not text, or too
    long: 80 characters for the name, 120 for the
    affiliation; `404` if the caller was never recorded
- **`GET /users/people`**
  - Needs: `users.read`
  - Answers: `200`, a list of
    `{sub, email, roles, first_seen_at, seen_at}`, by
    e-mail, at most 1000
  - Refuses: `403`
- **`GET /users/roles`**
  - Needs: `users.read`
  - Answers: `200`, a list of
    `{role, about, permissions}`
  - Refuses: `403`
- **`PUT /users/people/{sub}/roles/{role}`**
  - Needs: `users.grant`
  - Answers: `200`, `{sub, role, granted: true}`; twice
    is once
  - Refuses: `403`; `404` for a person or a role that
    does not exist
- **`DELETE /users/people/{sub}/roles/{role}`**
  - Needs: `users.grant`
  - Answers: `200`, `{sub, role, granted: false}`
  - Refuses: `403`; `404` if the person lacks the role;
    `409` for the last `users.grant` there is

Every route answers `401` without a valid token. A
refusal's body is `{error}`, the database's message.
Times are ISO 8601: Python keeps the database's offset,
JavaScript writes UTC, `...Z`; both are the same
instant.

## 3 The Manifest's Routes

After the starter's three, in the `routes` of the
service you take:

``` json
[
  {
    "method": "GET",
    "path": "/users/me",
    "signed_in": true
  },
  {
    "method": "PUT",
    "path": "/users/me/profile",
    "signed_in": true
  },
  {
    "method": "GET",
    "path": "/users/people",
    "signed_in": true
  },
  {
    "method": "GET",
    "path": "/users/roles",
    "signed_in": true
  },
  {
    "method": "PUT",
    "path": "/users/people/{sub}/roles/{role}",
    "signed_in": true
  },
  {
    "method": "DELETE",
    "path": "/users/people/{sub}/roles/{role}",
    "signed_in": true
  }
]
```

A `{sub}` or `{role}` is letters, digits, `-` and `_`,
up to 64: a Cognito `sub` is a UUID, and fits.

## 4 See Also

- [The tests](3-tests.md): next, held to this page
- [Tutorial 2's
  contract](../2-authorisation/2-contract.md): the
  accessors behind each route
