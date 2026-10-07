---
abstract: |
  Step 1 of tutorial 6: where uploads live, who reads
  and writes them, how they are named, counted and
  collected, and why they are py-api's. The goal, seven
  rules, the limits, and what it will not do.
date: 2026-10-07
keywords:
- tutorial
- uploads
- concept
kind: explanation
sources:
- dev/mock-store/server.py
- box/render.py
status: draft
subtitle: Step 1, what and why
title: "6.1 Uploads: the Concept"
version: v0.1.0
---

> [!NOTE]
> This concept is subject to refinement during the
> development process. Until [the
> contract](2-contract.md) exists, and wherever it is
> silent, this page is the source of truth.

## 1 The Goal

**Files on notes, kept for as long as a note needs
them, and not a moment longer.** Every decision below
was taken for the box's own uploads first, by its
owner; this carries them into a project.

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

## 2 The Rules

- **O1 Where: the static bucket, under `objects/`.**
  Never `www` or `docs`: a release syncs those with
  `--delete`, and would erase every upload. A release
  adds `static/` to the static bucket without deleting,
  and its role is refused `objects/` outright, so a
  release and the uploads never meet
- **O2 Who: anyone reads; members write, through py-api
  alone.** Reads at
  `https://static.<zone>/objects/...`, through
  Cloudflare: **(u=rw, a=r)**, as the notes, so an
  upload is as public as a note is readable.
  `objects.write` is a member's. py-api writes from the
  box, unsigned, as the box's own uploads go: no AWS
  credential in any container
- **O3 The key names its owner and its content:**
  `objects/<owner's tag>/<SHA-256 of the bytes>`. It
  changes with the content, so a key always holds the
  same bytes: no overwrite, no version, and Cloudflare
  may cache it for good. The owner's tag, the first 16
  hex digits of the SHA-256 of their `sub`, makes one
  object one owner's: two people uploading the same
  bytes have an object each, and one person uploading
  them twice has one
- **O4 What: six types, 1 MiB.** PNG, JPEG, GIF, WebP,
  PDF and plain text. Never HTML or SVG:
  `static.<zone>` would serve them as pages, their
  scripts running at your zone. 1 MiB is nginx's limit
  on every API host
- **O5 A note refers to its owner's own objects,** each
  stored, twenty at most
- **O6 References are counted, never kept.** One row a
  link; an object's references are those rows, so the
  count cannot drift from the truth
- **O7 What no note needs is collected after a grace.**
  Untouched for six hours by default, deleted from the
  bucket, then forgotten. The grace covers an upload
  whose note is not yet saved

## 3 Why py-api, and Python

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

## 4 What It Will Not Do

- **Keep anything private.** Something private belongs
  elsewhere, with a credential the box keeps out of
  containers
- **Take more than 1 MiB.** Larger needs the box's
  owner: a larger limit on one route, or uploads
  straight to S3
- **Rename or replace a file.** A new content is a new
  key; the old one goes when no note needs it

## 5 See Also

- [The contract](2-contract.md): next, then [the
  tests](3-tests.md)
