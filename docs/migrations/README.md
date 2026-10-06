---
abstract: |
  The project's one database: who owns its schema, what
  the services may do in it, how its migrations become
  an image the box runs before any service, and when
  the box will have it.
date: 2026-10-06
keywords:
- db
- migration
- dbmate
- postgres
kind: explanation
sources:
- migrations/Dockerfile
- migrations/sql/20261006120000_py_api_create_notes.sql
- box/render.py
status: draft
subtitle: One database, two logins, one image of
  migrations
title: The Database
version: v0.1.0
---

## 1 One Database, Shared by Name

The project has one PostgreSQL database, named for the
project, and every service with state keeps its part of
it there. A service's part is its prefix: `py-api` owns
every object named `py_api_*`, `js-api` every
`js_api_*`. The manifest names each service's prefix;
`make check` refuses a migration whose objects carry
another's.

For a small team, one database is simpler to run, back
up and reason about than one per service, and a prefix
is enough of a fence when the people are few. [The
database's conduct](../conduct/database.md) is the
discipline that makes it hold.

## 2 Two Logins

- **`<project>_migrator`** owns the database and its
  schema, and runs the migrations: nothing else does
- **`<project>`** is the services' login. It holds, by
  default privileges, rows on every table and `EXECUTE`
  on every function and procedure the migrator makes.
  It cannot create, alter or drop

In the template, `example_migrator` and `example`. A
service finds its login in `DATABASE_URL`.

## 3 The Migrations Image

`migrations/` is a unit of its own, as a service is:
its own `Dockerfile`, `build.sh` and `buildspec.yml`,
and its own image on the box,
`tu-rgb-sites-<project>-migrations`. The image is
dbmate, by digest, with every file of `migrations/sql/`
and `schema.sql`.

``` mermaid
---
config:
  themeVariables:
    edgeLabelBackground: "#d9eaf2"
  themeCSS: ".edgeLabel, .edgeLabel p, .labelBkg { background-color: #d9eaf2 !important; color: #5c7a8a !important; }"
---
flowchart LR
  tag(["A release tag"])
  image["The migrations image<br/>dbmate and migrations/sql/"]
  migrate["migrate<br/>once, as the migrator"]
  svc["The services<br/>as the project's login"]
  db[("PostgreSQL<br/>the project's database")]
  tag -->|"migrations/ changed"| image
  image -->|"the box pins its digest"| migrate
  migrate -->|"then"| svc
  migrate -->|"schema_migrations"| db
  svc -->|"rows, accessors"| db
  classDef network fill:#dbeafe,stroke:#3b82f6,color:#111
  class tag network
  classDef compute fill:#fff6eb,stroke:#804900,color:#804900
  class image,migrate,svc compute
  classDef storage fill:#dcfce7,stroke:#22c55e,color:#111
  class db storage
```

At every start of the stack the box runs the image
once, as the migrator: dbmate applies every migration
not yet in the ledger, `schema_migrations`, in the
order of their names. Every service waits for it; a
broken migration keeps them all down, rather than
letting one run on a schema it does not expect.

## 4 When the Box Has It

Not yet. The box's PostgreSQL, and a project's database
on it, is the last step of the box's `feature/postgres`
(the box's `todo.md` §50.2 decision 5). Until then:

- the dev stack has the database, its logins and its
  migrations, as the box will
- a release builds the migrations image and records its
  digest
- the box does not run it, and a service must not need
  its database to start

## 5 Folders

- `migrations/sql/`: the migrations,
  `<version>_<prefix>_<what>.sql`
- `migrations/schema.sql`: the schema they make, from
  dbmate's dump
- `migrations/.squawk.toml`: Squawk's settings
- `migrations/Dockerfile`, `build.sh`, `buildspec.yml`:
  the image; the last two are the box's, as in every
  image's folder

## 6 See Also

- [Write a migration](write-a-migration.md)
- [The database's conduct](../conduct/database.md)
- [How a release reaches the
  box](../onboarding/ci-cd.md)
