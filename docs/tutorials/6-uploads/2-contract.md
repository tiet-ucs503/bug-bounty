---
abstract: |
  Step 2 of tutorial 6: what the uploads promise. The
  routes, the accessors, the store's behaviour, what
  `GET /notes` adds, and what the box must give.
date: 2026-10-07
keywords:
- tutorial
- uploads
- routes
- contract
kind: reference
sources:
- dev/mock-store/server.py
- services/py-api/main.py
status: draft
subtitle: Step 2, what others may rely on
title: "6.2 Uploads: the Contract"
version: v0.1.0
---

## 1 Who Relies on It

- **The dashboard,** which uploads, links and shows
- **The box's owner,** who gives the bucket's policy
  and `store.env`
- **Anyone who reads,** at `static.<zone>/objects/`

## 2 The Routes

All at `https://py-api.<zone>`, each with
`Authorization: Bearer <access token>`; every answer
JSON, with `Cache-Control: no-store`.

- **`POST /objects/new`**
  - Takes: the file's bytes as the body, its type in
    `Content-Type`; no form, no multipart
  - Needs: `objects.write`
  - Answers: `201`, `{key, url, size, type}`; the same
    bytes again answer the same key
  - Refuses: `400` for no body; `413` over 1 MiB; `415`
    for a type not allowed; `403`; `502` if the bucket
    refuses
- **`GET /objects/mine`**
  - Needs: a token
  - Answers: `200`, a list of
    `{key, size, type, created_at, refs, url}`, newest
    first, 500 at most
- **`PUT /notes/{id}/objects`**
  - Takes: `{keys}`, the note's whole list, 20 at most
  - Needs: `notes.write`, and the note your own
  - Answers: `200`, `{id, keys}`
  - Refuses: `403`; `404` for no such note, or an
    object that is not yours or not stored; `422` for
    more than 20

**`GET /notes` adds beside:** each note now has
`objects`, a list of `{key, type}`. Nothing it had
before changes.

The manifest's lines, after the others in py-api's
`routes`:

``` json
[
  {
    "method": "POST",
    "path": "/objects/new",
    "signed_in": true
  },
  {
    "method": "GET",
    "path": "/objects/mine",
    "signed_in": true
  },
  {
    "method": "PUT",
    "path": "/notes/{id}/objects",
    "signed_in": true
  }
]
```

Under `/objects/`, where the box's zone counts requests
against Cloudflare's rate limit.

## 3 The Accessors

py-api's, in its migration; each takes the caller first
where there is one:

- **`py_api_object_add(caller, sha256, size, type)`:**
  `objects.write`; the key made here, never chosen by a
  caller; answers `{key, stored}`
- **`py_api_object_stored(caller, key)`:** the bucket
  holds it
- **`py_api_objects_mine(caller)`:** the caller's
  stored objects, each with `refs`, counted
- **`py_api_note_objects_set(caller, note, keys)`:**
  `notes.write`; refuses `P0002` for an object not the
  caller's or not stored
- **`py_api_notes_page(caller, before, limit)`:** the
  notes, each with its objects
- **`py_api_objects_to_collect(grace, limit)` and
  `py_api_objects_forget(keys)`:** the collector's, no
  caller

And the users unit's: `objects.write`, a cell for
`member` in the matrix, by a users migration.

## 4 The Store

The box's static bucket, at S3's path-style address,
and the stack's mock behave alike:

- **A write:** `PUT <store>/objects/<key>`, unsigned,
  with `x-amz-checksum-sha256`, the body's SHA-256 in
  base64; `200`, or `400` `BadDigest` for a mismatch
- **A read:** `GET <static>/objects/<key>`, with the
  type it was stored with
- **No write through the static host:** `403`
- **A delete:** `204`, whether or not it was there
- **Keys outside `objects/`:** never written; the mock
  answers `404`

## 5 What the Box Must Give

Locally, the stack mocks all of it. On the box, its
owner adds, once a project:

- **The static bucket's policy:** `PUT` and `DELETE` on
  `objects/*` from the box's Elastic IP, as the box's
  own static bucket admits for its uploads
- **`store.env`,** beside `cognito.env`:
  `STORE_URL=https://s3.ap-south-1.amazonaws.com/static.<zone>`,
  S3's path-style address, since the bucket's name has
  dots; and `STATIC_URL=https://static.<zone>`
- **Cloudflare's rate limit** on paths that start with
  `/objects/`. On the box's own zone it exists already,
  the zone's one rule, and counts in every host: the
  uploads at `py-api.<zone>/objects/new` and the reads
  at `static.<zone>/objects/...` alike. A project on a
  zone of its own has it only if the owner adds it.
  Whether it counts reads that Cloudflare answers from
  its cache is not settled here

> [!WARNING]
> Every project's containers leave the box from the
> same Elastic IP. A policy that admits it admits every
> project on the box, so another's code could write to
> your `objects/`. The box's owner weighs this before
> admitting it; see the box's
> `todo-project-template.md` §51.4.

## 6 See Also

- [The tests](3-tests.md): next, held to this page
