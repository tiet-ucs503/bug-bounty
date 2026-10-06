---
abstract: |
  Files on notes. Each upload an object in the
  project's static bucket, under `objects/`, read by
  anyone at `static.<zone>` and written only through
  py-api; its key names its owner and its content, so
  it is never overwritten; each note's references to it
  counted, and an object no note needs collected after
  a grace. The design, why Python, what the box must
  give, and four parts that build it: the store, the
  database, the service, the UI.
date: 2026-10-06
keywords:
- tutorial
- uploads
- static
- s3
- db
- py-api
kind: tutorial
sources:
- dev/mock-store/server.py
- box/render.py
status: draft
subtitle: Files on notes, in the static bucket
title: 7 Uploads
version: v0.1.0
---

## 1 Before You Start

- [6 A Svelte UI](../6-a-svelte-ui.md): the notes, in
  py-api and in the dashboard
- A local stack whose render has the mock store:
  `make dev`, or the native stack's `start`, after this
  template's v0.1.0

## 2 The Parts

  -------------------------------------------------------
  Part                           What it adds
  ------------------------------ ------------------------
  [1 The store](1-the-store.md)  The static bucket's
                                 `objects/` on your
                                 machine: write, read,
                                 refuse

  [2 The                         Objects, their owners,
  database](2-the-database.md)   the notes' references,
                                 and what may be
                                 collected

  [3 The                         py-api's upload, the
  service](3-the-service.md)     notes' links, and the
                                 collector

  [4 The UI](4-the-ui.md)        A file selector, then
                                 attachments shown, then
                                 drag and drop
  -------------------------------------------------------

## 3 The Design

Every decision below was taken for the box's own
uploads first, by its owner; this carries them into a
project.

- **Where:** the project's **static bucket**, under
  `objects/`. Never `www` or `docs`: a release syncs
  those with `--delete`, and would erase every upload.
  A release adds `static/` to the static bucket without
  deleting, and its role is refused `objects/`
  outright, so a release and the uploads never meet
- **Who reads:** anyone, at
  `https://static.<zone>/objects/...`, through
  Cloudflare. **(u=rw, a=r)**, as the notes: an upload
  is as public as a note is readable. Something private
  belongs elsewhere
- **Who writes:** py-api alone, from the box, unsigned,
  as the box's own uploads go: no AWS credential in any
  container
- **The key:**
  `objects/<owner's tag>/<SHA-256 of the bytes>`. It
  changes with the content, so a key always holds the
  same bytes: no overwrite, no version, and Cloudflare
  may cache it for good. The owner's tag, the first 16
  hex digits of the SHA-256 of their `sub`, makes **one
  object one owner's**: two people uploading the same
  bytes have an object each
- **The count:** a note refers to objects through
  links, one row each; an object's references are those
  rows, **counted, never kept**, so the count cannot
  drift from the truth
- **The collector:** an object no note refers to, and
  untouched for a grace, six hours by default, is
  deleted from the bucket, then forgotten. The grace
  covers an upload whose note is not yet saved

``` mermaid
---
config:
  themeVariables:
    edgeLabelBackground: "#d9eaf2"
  themeCSS: ".edgeLabel, .edgeLabel p, .labelBkg { background-color: #d9eaf2 !important; color: #5c7a8a !important; }"
---
graph TD
  A(["A member"])
  B["A new object"]
  C["A note"]
  D["An object no note refers to"]
  E[\"The collector, after the grace"/]
  A -- "uploads" --> B
  A -- "edits" --> C
  C -- "refers to" --> B
  C -. "lets go" .-> D
  D ==> E
```

## 4 Why Python, and py-api

The unit decides, more than the language. **A file is
referred to by a note, and the notes are py-api's.**
Linking an object to a note, and counting it, must
happen in the same transaction as the note's own
change, in tables under one prefix; uploads in another
unit would make every note's save a call across units.
So uploads belong where the notes are.

And Python does make the service's half short:
`await request.body()`, `hashlib.sha256` and
`urllib.request` from the standard library are the
whole of reading, naming and storing an upload; nothing
new to install. Node would be about as short, with a
content-type parser added to Fastify for raw bodies,
`node:crypto` and `fetch`. Had the notes been
`js-api`'s, uploads would be too, in JavaScript.

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

## 6 The Limits

- **1 MiB an upload,** nginx's limit on every API host.
  Larger needs the box's owner: a larger limit on one
  route, or uploads straight to S3, which need a
  credential the box keeps out of containers
- **Six types:** PNG, JPEG, GIF, WebP, PDF and plain
  text. Never HTML or SVG: `static.<zone>` would serve
  them as pages, their scripts running at your zone
- **Twenty objects a note**

## 7 See Also

- [1 The store](1-the-store.md): begin
- [The database's conduct](../../conduct/database.md)
