---
abstract: |
  The discipline that lets several services share one
  database: every name under its service's prefix, the
  basic reading and writing done by functions and
  procedures in the database, and the services calling
  those, not the tables.
date: 2026-10-06
keywords:
- db
- conduct
- postgres
- migration
kind: explanation
sources:
- migrations/sql/20261006120000_py_api_create_notes.sql
- box/render.py
status: draft
subtitle: Prefixes, accessors, and what a service may
  touch
title: The Database's Conduct
version: v0.1.0
---

## 1 Every Name Under Its Prefix

A service's tables, views, functions, procedures,
indexes, sequences, types and triggers are all named
`<prefix>_*`, its prefix from the manifest:
`py_api_notes`, `py_api_note_add`. A migration makes
the objects of one service alone, and its file name
carries that prefix. `make check` refuses either
broken, so the fence holds without anyone being
careful.

A service reads and writes its own objects alone.
Another service's data is that service's to give,
through its API, not through its tables, with one
exception: a function the other unit **publishes**
(§3).

## 2 Accessors in the Database

The basic reading and writing of a service's data are
functions and procedures beside the tables, written in
the same migration:

``` sql
CREATE OR REPLACE FUNCTION py_api_note_add(p_owner text, p_body text) RETURNS bigint
  LANGUAGE sql AS $$
  INSERT INTO py_api_notes (owner, body) VALUES (p_owner, p_body) RETURNING id
$$;
```

The service calls the accessor,
`SELECT py_api_note_add($1, $2)`, not the table. Why:

- **Faster:** one round trip, the plan made once in the
  database, rather than the logic and its queries
  spread through the API layer
- **One place for the rule:** a limit, a default or a
  check written once, beside the data, for every caller
- **A smaller surface:** the table's shape can change
  behind an accessor that keeps its signature

Keep in the service what is not data: the caller's
identity, from their token; the HTTP; calls to other
services. The caller's **rights** are data, and are
checked beside it: an accessor that acts for a caller
takes the caller first, checks before it acts, and
refuses with an SQLSTATE the service turns into HTTP
(`42501` for `403`, `P0002` for `404`). A service that
forgets a check cannot skip it ([2 What each may
do](../tutorials/2-authorisation.md) §5).

## 3 What a Service May Touch

- **Its own accessors,** first
- **Its own tables,** for what no accessor yet does;
  then write the accessor
- **Another unit's published functions,** and nothing
  else of that unit. A unit publishes a function by
  saying so in its comment,
  `COMMENT ON FUNCTION ... IS 'published: ...'`, and
  keeps its signature as a promise to every caller. The
  users unit's `users_may` is the example: every unit
  asks it whether a person may do a thing, and none
  reads `users_*` tables
- **Never** another service's other objects, and never
  the schema: the project's login holds rows and
  `EXECUTE`, and only the migrator changes the schema.
  Nor dbmate's ledger, `schema_migrations`, which the
  project's login may not touch

The fence is discipline, not a lock: one login holds
`EXECUTE` on everything. A login per unit would make it
a lock; the box's `feature/postgres` has not chosen
that yet.

## 4 Migrations

- **One change a file,** under one prefix
- **Never edit one that has run** anywhere but your
  machine
- **Add, then use, then remove,** a release each, so
  the code before and after both run on the schema
  between
- **An accessor's signature is a promise:** change it
  by adding a new one beside it, and drop the old once
  nothing calls it

[Write a migration](../migrations/write-a-migration.md)
has the steps.

## 5 See Also

- [The database](../migrations/README.md): one
  database, its logins
- [How these pages are written](README.md): the other
  conduct
