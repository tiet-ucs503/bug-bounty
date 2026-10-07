---
abstract: |
  Step 2 of tutorial 5: what tutorials 6 and 7 may rely
  on, and nothing about how. The migration, the notes'
  accessors with the permission each needs and how it
  refuses, py-api's four routes, their entries in the
  manifest, and the refusals as HTTP. Once written, the
  contract outranks the concept wherever both speak.
date: 2026-10-07
keywords:
- tutorial
- notes
- contract
- db
- py-api
kind: reference
sources:
- tools/native-dev.sh
status: draft
subtitle: Step 2, what others may rely on
title: "5.2 Notes: the Contract"
version: v0.1.0
---

## 1 Who Relies on It

- **Tutorial 6,** the dashboard: it calls the routes,
  and shows what `/users/me`'s permissions allow
- **Tutorial 7,** uploads: its accessors add to the
  notes beside these, and its references point at
  `py_api_notes`
- **Any client of py-api,** by the routes, and
  `docs/py-api/api.md`'s entries for them

## 2 The Migration

One file in `migrations/sql/`, after tutorial 3's:
`<version>_py_api_create_notes.sql`. Its up makes the
table and the accessors, then brings the permissions:

- **`notes.read`,** for `reader` and `member`
- **`notes.write`,** for `member`

Its down takes both permissions away first, by
`users_permission_drop`, then drops what the up made.

## 3 The Accessors

- **`py_api_note_new(caller, body)`**
  - Needs: `notes.write`
  - Answers: the note's `id`; the caller owns it
  - Refuses: `42501`; `23514` for a body out of bounds
- **`py_api_notes_all(caller, before, limit)`**
  - Needs: `notes.read`
  - Answers: rows: `id`, `body`, `mine`, `created_at`,
    `updated_at`; newest first
  - Refuses: `42501`
- **`py_api_note_edit(caller, id, body)`**
  - Needs: `notes.write`, and the owner
  - Answers: nothing
  - Refuses: `42501`; `P0002` if there is no such note;
    `23514`
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
- **None is published.** The notes' accessors are
  py-api's to call; another unit asks py-api, by its
  routes

## 4 The Routes

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

## 5 The Manifest's Routes

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

## 6 The Refusals

Each accessor refuses with an SQLSTATE, which py-api
turns into HTTP, as [tutorial 2's
contract](../2-authorisation/2-contract.md) §3 gives
them: `42501` 403, `P0002` 404, `23514` 400. A body out
of bounds never reaches the database: py-api answers
`422` first.

## 7 See Also

- [The tests](3-tests.md): next, held to this page, and
  [the implementation](4-implementation.md): after it
- [The cycle](../../conduct/the-cycle/README.md) §2:
  what a contract is for, and how it changes
