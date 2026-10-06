---
abstract: |
  Every key of box/project.json, what the box does with
  it, and the rules make check holds it to.
date: 2026-10-06
keywords:
- manifest
- render
- routes
kind: reference
sources:
- box/project.json
- box/render.py
status: draft
title: The Manifest, Key by Key
version: v0.1.0
---

## 1 The Project

name
: 2 to 16 characters, lower case and digits, a letter
  first. Names every resource on the box,
  `tu-rgb-sites-<name>-<service>`

description
: Free text, for the reader

github
: This repository, `owner/name`. The project's CI role
  trusts its `v*` tags alone

database
: `true` for the project's one database, with its
  migrations in `migrations/sql/`; `false` if left out.
  The dev stack makes it today; the box at the last
  step of its `feature/postgres`. See [The
  database](../migrations/README.md)

ui.dev_callback_urls
: `http://localhost:<port>/` addresses where a
  developer runs the UI. Each is a sign-in callback,
  and an allowed CORS origin

## 2 Each Service

name
: 2 to 20 characters, lower case, digits and hyphens.
  The host's label, `<name>.<zone>`; not `www`,
  `static` or `docs`, which the box keeps. The folder
  in `services/` of the same name

language
: `node` or `python`; it chooses the health check's
  command

port
: 1024 to 65535, the port the service listens on

memory_mib
: 64 to 512; 192 if left out. A hard limit: past it the
  container is killed and restarted

prefix
: The service's part of the database: every object its
  migrations make is named `<prefix>_*`, and every
  migration file carries it. Lower case, digits and
  `_`; the name with `_` for `-` if left out; no other
  service's. See [The database's
  conduct](../conduct/database.md)

routes
: The allow-list, each with `method`, `path` and
  `signed_in`

## 3 Each Route

method
: `GET`, `POST`, `PUT`, `PATCH` or `DELETE`. `GET`
  admits `HEAD`

path
: Exact, from `/`. A segment is letters, digits and
  `._-`, or a parameter `{name}`, which matches 1 to 64
  letters, digits, `_` or `-`. No `.` or `..` segment,
  no `//`

signed_in
: Whether the service needs a token. `true` if left
  out. The box does not enforce it; the probes check
  it, and the service must

Every service needs `GET /health`, not signed in.

## 4 What Can Go Wrong

- **`needs GET /health, signed_in false`.** Add the
  route; the box and the probes check it
- **`over 48 characters`.** The project's and the
  service's names together are too long for the box's
  names; shorten either

## 5 See Also

- [Hand a change to the box's owner](hand-over.md):
  what a change to the manifest sets going
