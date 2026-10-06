---
abstract: |
  Seven tutorials, in order, that take a fork of the
  template from a sign-in to a notes dashboard with
  uploads: who comes in, what each person may do, the
  database that holds both, a `users` service in Python
  or JavaScript, a Svelte UI, and files in the static
  bucket. What you build, what you need, and the
  conventions every page shares.
date: 2026-10-06
keywords:
- tutorial
- auth
- authz
- db
- ui
- uploads
kind: tutorial
sources:
- box/project.json
- Makefile
- tools/native-dev.sh
status: draft
subtitle: From a sign-in to a notes dashboard with
  uploads
title: Tutorials
version: v0.1.0
---

## 1 What You Build

A small project of your own, in your fork, one piece a
page:

``` mermaid
---
config:
  themeVariables:
    edgeLabelBackground: "#d9eaf2"
  themeCSS: ".edgeLabel, .edgeLabel p, .labelBkg { background-color: #d9eaf2 !important; color: #5c7a8a !important; }"
---
flowchart LR
  browser(["The dashboard<br/>Svelte, at www"])
  cognito["Cognito<br/>the box's pool"]
  users["users<br/>who comes in, who may what"]
  notes["py-api<br/>notes and uploads"]
  db[("The project's database<br/>users_*, py_api_*")]
  bucket[("The static bucket<br/>objects/")]
  browser -->|"signs in"| cognito
  browser -->|"Bearer token"| users
  browser -->|"Bearer token"| notes
  users -->|"userInfo: the e-mail"| cognito
  users -->|"users_admit, users_grant"| db
  notes -->|"py_api_*, which ask users_may"| db
  notes -->|"PUT, DELETE"| bucket
  browser -->|"reads"| bucket
  classDef network fill:#dbeafe,stroke:#3b82f6,color:#111
  class cognito network
  classDef compute fill:#fff6eb,stroke:#804900,color:#804900
  class users,notes compute
  classDef storage fill:#dcfce7,stroke:#22c55e,color:#111
  class db,bucket storage
```

1.  [Who comes in](1-authentication.md): the rules of
    who may sign in, tried in the database
2.  [What each may do](2-authorisation.md): the access
    control matrix, and notes as (u=rw, a=r), tried
3.  [Make it a migration](3-the-migration.md): both as
    migrations, each proved down and up
4.  [users in Python](4-users-in-python.md): the
    `users` service
5.  [users in JavaScript](5-users-in-javascript.md): or
    the same, in JavaScript
6.  [A Svelte UI](6-a-svelte-ui.md): the dashboard, who
    you are, the notes, the people
7.  [Uploads](7-uploads/README.md): files on notes, in
    the static bucket, collected when no note needs
    them

Take 4 **or** 5: the same service, the same routes, the
same database, in the language your team writes. The
rest are in order; each starts where the one before
ended.

Every step on these pages was run, as written, in a
fork of the template v0.1.0 on 2026-10-06: on the
native stack, and in containers under rootless Podman.

## 2 Before You Start

- **A fork of the template,** and a shell at its root
- **A local stack,** either:
  - [the dev stack](../onboarding/local-dev.md), with
    Docker or [Podman](../onboarding/podman.md): hosts
    at `*.localhost:8080`;
  - [the native stack](../onboarding/shared-box.md),
    without containers or root: hosts at
    `*.localhost:<your NGINX_PORT>`
- **`curl`, `jq` and `psql`,** and Node 24 from page 6
  on
- **Reading SQL,** and Python or JavaScript

Nothing here touches the box or AWS. What reaches the
box, and what its owner must add first, each page says
at its end.

## 3 Conventions

Each page's commands use these settings; tutorial 7
alone needs the last two. Set them once in each shell,
for your stack.

For the dev stack:

``` sh
H=localhost:8080
MOCK_URL=http://localhost:9000
MIGRATOR_URL='postgres://example_migrator:dev-only@localhost:5432/example?sslmode=disable'
DATABASE_URL='postgres://example:dev-only@localhost:5432/example?sslmode=disable'
STORE_URL=http://localhost:9100/static.localhost
STATIC_URL=http://static.localhost:8080
```

For the native stack, from your own ports; `env.sh`
sets the database's and the store's four itself:

``` sh
. dev/out/native/env.sh
H=localhost:${NGINX_PORT}
MOCK_URL=http://localhost:${MOCK_PORT}
```

`example` is the template's project name; yours, once
you rename it in `box/project.json`.

**A person, by a token.** The mock signs anyone in as
anyone. `make dev-token` asks it for an access token,
and remembers the e-mail you give, as Cognito would,
for its `userInfo`:

``` sh
A=$(make -s dev-token MOCK_URL=${MOCK_URL} SUB=alice)
Y=$(make -s dev-token MOCK_URL=${MOCK_URL} SUB=you EMAIL=you@example.org)
```

`EMAIL` defaults to `<SUB>@example.org`, and
`VERIFIED=false` makes it unverified.

**Expect** before a command says what it prints when
all is well.

## 4 The Rules These Pages Keep

- **The box decides nothing about your people.** It
  checks the token's shape at nginx and nothing more.
  Who may come in and what they may do are yours, in
  your database
- **The database decides.** Every accessor takes the
  caller first, and refuses with an SQLSTATE the
  service turns into HTTP. A service that forgets a
  check cannot skip it
- **One thing, done well,** a unit each: `users` for
  people and roles, `py-api` for notes and uploads.
  [The philosophy](../conduct/philosophy.md)

## 5 See Also

- [The database's conduct](../conduct/database.md):
  prefixes, accessors, and the one function a unit
  publishes
- [Write a
  migration](../migrations/write-a-migration.md)
- [The UI](../ui/README.md)
