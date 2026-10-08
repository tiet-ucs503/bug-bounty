---
abstract: |
  The rules every service's API keeps: its reference is
  made from its routes, never written by hand; Scalar
  shows it, on the service's own host; each route says
  who may call it and what it refuses; and the manifest
  and the routes are held to each other by a test.
date: 2026-10-08
keywords:
- conduct
- api
- openapi
- scalar
- reference
kind: explanation
sources:
- services/py-api/main.py
- services/js-api/server.js
- box/render.py
status: draft
subtitle: A reference made from the routes, shown by
  Scalar
title: The API's Conduct
version: v0.1.0
---

Five rules, A1 to A5, for whoever adds a route to a
service. The starters keep all five from their first
route; a route you add keeps them by being written as
theirs are.

## 1 A1 The Reference Is Made, Not Written

**Each service answers `GET /openapi.json`: an OpenAPI
document made from its routes as they are.** Nobody
writes it, so it cannot fall behind the code.

- **py-api:** FastAPI makes it. FastAPI's own `/docs`
  and `/redoc` stay off
- **js-api:** `@fastify/swagger` makes it, from each
  route's `schema`
- **Another language:** whatever makes the document
  from the routes themselves. A file kept by hand
  beside the code is not this

## 2 A2 Scalar Shows It

**Each service answers `GET /scalar-ui`:
[Scalar](https://scalar.com/)'s page of that
document,** on the service's own host. A reader sees
every route, and tries one from the page, with a token
pasted in.

- **One file from elsewhere, and only one:** Scalar's
  script, from jsDelivr, named by its exact version and
  by its SHA-384. A browser refuses a file that does
  not match
- **Confined:** the page's `Content-Security-Policy`
  admits that script, the styles it injects, and calls
  to its own host. Nothing may frame it
- **Quiet:** its settings turn off Scalar's telemetry,
  its fonts, and its own tools, the AI, the MCP and the
  sharing among them
- **A new version of Scalar** is a new version and a
  new hash, together, in one commit

The page asks jsDelivr for its script, so jsDelivr
learns of each visit. [The UI's conduct](ui.md), U8,
forbids that for the UI; it is allowed here, for a
developer's page, because the alternative is a file of
four megabytes in every image.

## 3 A3 Each Route Says Who and What

**A route describes itself in the code:** who may call
it, what it answers, and each refusal with its status.
The reference shows those words.

``` python
@app.get("/notes")
def notes(before: int | None = None, authorization: str | None = Header(default=None)):
    """`notes.read`. `?before=<id>` pages back. `200` and a list of `{id, body, mine, created_at, updated_at}`,
    newest first, 50 at most. `403` without it"""
```

- **The first words are who:** `Anyone`, `Signed in`,
  or the permission, `notes.read`
- **A route that needs a token is marked.** In py-api,
  by taking the `Authorization` header as a parameter,
  or `openapi_extra=SIGNED_IN` where the route reads
  the header itself; in js-api, `security: SIGNED_IN`
  in its `schema`. Scalar then offers the token's field
- **Every refusal the route can give,** not only the
  common ones

## 4 A4 The Manifest and the Routes Agree

**A route is in `box/project.json` and in the code, or
in neither.** nginx passes what the manifest names; the
reference shows what the code has. Three checks hold
them together, none needing anyone to be careful:

- **`make check`** refuses a service whose manifest
  lacks `GET /openapi.json` or `GET /scalar-ui`, each
  not signed in, as it refuses one without
  `GET /health`
- **Each starter's own tests** compare the manifest's
  routes for the service with the reference's, both
  ways, and whether each asks for a token. A route
  added to one and not the other fails `make test`
- **The same test** fails a route with no description

So a tutorial that adds routes adds them to the
manifest before it runs the service's tests.

## 5 A5 The Page Beside It

**`docs/<service>/api.md` holds what the made reference
cannot:** the host, what the box answers before the
service does, and an entry a route in the same words as
its description. The pages are read when the service is
down, and by someone deciding whether to call it at
all.

- **Written together:** a route, its description, its
  line in the manifest and its entry in `api.md`, in
  one commit
- **Where they differ, the code's is right,** and the
  page is the thing to mend

## 6 What Is Public

The reference is for anyone: both routes are not signed
in, as the pages are public. It tells what routes there
are and who may call them, not anything a caller holds.
A route whose existence is itself a secret does not
belong in a service behind this box.

## 7 See Also

- [The manifest, key by
  key](../onboarding/manifest.md): the allow-list
- [The database's conduct](database.md): where a
  refusal comes from
- [4 /users](../tutorials/4-users/README.md): six
  routes written this way, in both languages
