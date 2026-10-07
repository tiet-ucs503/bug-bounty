---
abstract: |
  Step 2 of tutorial 6: the notes routes, what each
  takes and answers, and the manifest's lines; and what
  the dashboard relies on: `/users`, and the keys of
  its `config.js`.
date: 2026-10-07
keywords:
- tutorial
- ui
- routes
- contract
kind: reference
sources:
- services/py-api/main.py
- ui/config.example.js
status: draft
subtitle: Step 2, what others may rely on
title: "6.2 A Svelte UI: the Contract"
version: v0.1.0
---

## 1 Who Relies on It

- **The dashboard,** on the notes routes and on
  `/users`
- **Tutorial 7,** uploads, which adds to the notes
- **The release,** which builds `ui/` and writes its
  `config.js`

## 2 The Notes Routes

All at `https://py-api.<zone>`, each with
`Authorization: Bearer <access token>`; every answer
JSON, with `Cache-Control: no-store`.

- **`GET /notes?before=<id>`**
  - Needs: `notes.read`
  - Answers: `200`, a list of
    `{id, body, mine, created_at, updated_at}`, newest
    first, 50 at most; `before` pages back
  - Refuses: `403`
- **`POST /notes`**
  - Takes: `{body}`, 1 to 10,000 characters
  - Needs: `notes.write`
  - Answers: `201`, `{id}`
  - Refuses: `403`; `422` for a body out of bounds
- **`PUT /notes/{id}`**
  - Takes: `{body}`, as for `POST`
  - Needs: `notes.write`, and the note your own
  - Answers: `200`, `{id}`
  - Refuses: `403`, `not your note` or for want of
    `notes.write`; `404` for no such note; `422`
- **`DELETE /notes/{id}`**
  - Needs: as for `PUT`
  - Answers: `200`, `{id}`
  - Refuses: as for `PUT`

Every route answers `401` without a valid token.

## 3 The Manifest's Routes

After the others in py-api's `routes`:

``` json
[
  {
    "method": "GET",
    "path": "/notes",
    "signed_in": true
  },
  {
    "method": "POST",
    "path": "/notes",
    "signed_in": true
  },
  {
    "method": "PUT",
    "path": "/notes/{id}",
    "signed_in": true
  },
  {
    "method": "DELETE",
    "path": "/notes/{id}",
    "signed_in": true
  }
]
```

## 4 What the Dashboard Relies On

- **`/users`,** as [tutorial 4's
  contract](../4-users/2-contract.md) §2 gives it, at
  the service that serves it
- **`config.js`** at the site's root, a module whose
  default export has:
  - `clientId`: your UI's client in the box's pool
  - `authDomain`: the pool's sign-in domain
  - `zone`: your zone, for `https://<service>.<zone>`
  - `apis`: your services, as the manifest names them
  - `apiUrl`, optional: a function from a service's
    name to its address, for a local stack
  - `staticUrl`, optional: the static bucket's address
- **The release** builds `ui/` when `ui/package.json`
  exists, and syncs `ui/dist/` to `www`

## 5 See Also

- [The tests](3-tests.md): next, held to this page
- [Release the UI](../../ui/release.md): how
  `config.js` is written
