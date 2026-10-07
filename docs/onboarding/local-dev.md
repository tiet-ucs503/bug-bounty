---
abstract: |
  Run the project on your own machine as the box runs
  it: the box's nginx in front of your services, a mock
  of Cognito's sign-in, a PostgreSQL database, and the
  static and docs buckets as folders. For anyone
  changing a service or the UI.
date: 2026-10-06
keywords:
- local-dev
- mock
- auth
- db
- nginx
kind: how-to
sources:
- box/render.py
- dev/mock-auth/server.py
- ui/config.dev.example.js
- Makefile
status: draft
subtitle: The box's nginx, a mock sign-in, PostgreSQL
  and the buckets as folders
title: A Local Stack That Mirrors the Box
version: v0.1.0
---

## 1 Before You Start

- **Docker,** with Compose 2.20 or later
- **GNU `make`, `jq` and `curl`;** Python 3 for the
  render; md-preview, if you want these pages at
  `docs.localhost`
- **All of it by one command,** with your system's
  packages: `make install-deps STACK=docker`, then
  `make check-deps STACK=docker`. [The
  tutorials](../tutorials/README.md) §2 says what each
  tool is for, and §6 what each trusts
- **Nothing to undo:** the stack binds only to
  `127.0.0.1`, and `make dev-down` stops it

## 2 What Is Mirrored, What Is Mocked

`make dev` renders the stack from your manifest into
`dev/out/`, the way `make render` renders the box's
pieces:

``` mermaid
---
config:
  themeVariables:
    edgeLabelBackground: "#d9eaf2"
  themeCSS: ".edgeLabel, .edgeLabel p, .labelBkg { background-color: #d9eaf2 !important; color: #5c7a8a !important; }"
---
flowchart LR
  browser(["Browser<br/>localhost:5173"])
  nginx["nginx<br/>*.localhost:8080"]
  svc["Your services<br/>built from services/"]
  auth["mock-auth<br/>localhost:9000"]
  store[("mock-store<br/>static's objects/")]
  db[("PostgreSQL<br/>localhost:5432")]
  files[("Folders<br/>static, docs")]
  browser -->|"signs in"| auth
  browser -->|"Bearer token"| nginx
  nginx --> svc
  nginx --> files
  nginx -->|"GET objects/"| store
  svc -.->|"PUT, DELETE"| store
  svc -->|"the pool's keys"| auth
  svc -.->|"DATABASE_URL"| db
  classDef network fill:#dbeafe,stroke:#3b82f6,color:#111
  class auth network
  classDef compute fill:#fff6eb,stroke:#804900,color:#804900
  class nginx,svc compute
  classDef storage fill:#dcfce7,stroke:#22c55e,color:#111
  class db,files,store storage
```

  ----------------------------------------------------
  The box              Here
  -------------------- -------------------------------
  Cloudflare, TLS,     None: plain HTTP on
  origin pulls         `127.0.0.1:8080`

  nginx: the           The same servers, rendered from
  allow-list, CORS,    the same manifest, the box's
  write limits, 1 MiB  nginx by digest; writes limited
                       by your address, not
                       Cloudflare's header

  Cognito, the box's   `mock-auth`: the same
  pool                 endpoints, `userInfo` among
                       them, and token shapes, a key
                       made at start, any name
                       accepted

  No database yet      PostgreSQL 17: the project's
                       one database and its two
                       logins, `migrations/sql/`
                       applied by dbmate at every
                       start

  `static` and `docs`  Folders, read-only: `static/`,
  buckets              `docs/_site/`

  The `static`         `mock-store`, on
  bucket's `objects/`, `localhost:9100`: S3's unsigned
  written by services  writes and its checksum check;
                       read through nginx

  Images built on      Built here, for your machine's
  arm64 by CodeBuild   architecture
  ----------------------------------------------------

> [!WARNING]
> The mock admits anyone as anyone, and the database's
> password is `dev-only`. Never run the stack anywhere
> but your own machine.

## 3 Start the Stack

Expect the build's lines, then five containers started:
`nginx`, `mock-auth`, `db` and one per service:

``` sh
make dev
```

Then expect each service `healthy`:

``` sh
docker compose -f dev/out/compose.yml ps
```

## 4 Call a Service

Through nginx, as the box would answer. `*.localhost`
names this machine, in curl and in browsers. Expect
`{"status":"ok","service":"js-api"}`:

``` sh
curl -s http://js-api.localhost:8080/health
```

A signed-in route, with a token from the mock for a
user of your choosing. Expect `200` and the user named
as the caller:

``` sh
TOKEN=$(make -s dev-token SUB=asha GROUPS=admin)
curl -s -X POST -H "Authorization: Bearer ${TOKEN}" -H 'Content-Type: application/json' -d '{"x": 1}' http://js-api.localhost:8080/echo
```

The allow-list holds here too: expect `404` for a path
the manifest does not name.

``` sh
curl -s -o /dev/null -w '%{http_code}\n' http://js-api.localhost:8080/nowhere
```

## 5 Run the UI Against It

Point the UI at the mock and at nginx, then serve it:

``` sh
cp ui/config.dev.example.js ui/config.js
make ui
```

Open `http://localhost:5173/`. **Sign in** shows the
mock's form: any user, email and groups. The calls go
to `http://<service>.localhost:8080`, through the same
CORS the box applies. Copy `ui/config.example.js` back
before a release.

## 6 Use the Database

The box has no database yet; the stack has one, as the
box will have it after its `feature/postgres`. With
`"database": true` in the manifest, the project's one
database and its two logins are made, and
`migrations/sql/` applied before any service starts:
[Write a
migration](../migrations/write-a-migration.md). Every
service finds the project's login in `DATABASE_URL`.
From your machine, as that login, expect a `psql`
prompt:

``` sh
psql 'postgres://example:dev-only@localhost:5432/example'
```

The data lives in the stack's volume, `db`, between
runs.

## 7 Read the Buckets

Expect the sample file's text, and then these pages:

``` sh
curl -s http://static.localhost:8080/hello.txt
curl -s -o /dev/null -w '%{http_code}\n' http://docs.localhost:8080/
```

Put what your UI reads from `static.<zone>` in
`static/`, which a release adds to the bucket. The
bucket's `objects/` is the other half, written by your
services at run time, never by a release: here the mock
store holds it, and nginx serves it at
`static.localhost:8080/objects/` ([7.1 The
store](../tutorials/7-uploads/1-the-store.md)).

## 8 After a Change

- **A service's code:** rebuild that service alone. Its
  name in the stack is your project's `name` and the
  service's, `example-js-api` for the template

  ``` sh
  docker compose -f dev/out/compose.yml up --build -d example-js-api
  ```

- **The manifest:** `make dev` again. It renders afresh
  and restarts what changed; restart nginx so it reads
  the new servers:

  ``` sh
  docker compose -f dev/out/compose.yml restart nginx
  ```

- **The UI:** reload the page; `make ui` serves `ui/`
  as it is, or runs Vite's dev server once `ui/` has a
  `package.json`

- **A setting of your own** for every service, such as
  a shorter interval to try something: `KEY=value`
  lines in `dev/dev.env`, which git ignores, then
  `make dev`. The native stack reads the same file at
  `start`. The value runs to the line's end, spaces and
  all; no quotes

## 9 Stop

Expect each container stopped and removed; the
database's volume is kept:

``` sh
make dev-down
```

> [!CAUTION]
> `down -v` deletes the volume, and the database with
> it. Nothing else holds a copy.

``` sh
docker compose -f dev/out/compose.yml down -v
```

## 10 Without Docker, or Without Root

The tests need nothing but the languages: [js-api's
development page](../js-api/develop.md) and
[py-api's](../py-api/develop.md). For more, there are
three ways, by what your machine allows: §11 to §13.

## 11 A Shared Box Without Root

Everything in your own directory, no containers: the
tools from conda-forge, PostgreSQL on a port of your
own, the box's nginx in front of your services, the
mock sign-in, the UI through SSH. One script runs it,
`tools/native-dev.sh`: [Develop on a shared box without
root](shared-box.md), step by step.

## 12 Podman, Without Root

The same compose stack in rootless Podman, where the
box's administrator has given you subordinate IDs:
`make dev COMPOSE=podman-compose`. [Run the stack with
rootless Podman](podman.md), step by step, with how it
differs from Docker.

## 13 A Thin Client

Run the stack on a machine that has Docker, or on the
shared box as above, and forward its ports over SSH. On
the thin client the browser then finds
`localhost:5173`, `js-api.localhost:8080` and
`localhost:9000` on its own loopback, forwarded, and
the pages' addresses work as written:

``` sh
DEV_HOST=dev.example.org
ssh -N -L 5173:localhost:5173 -L 8080:localhost:8080 -L 9000:localhost:9000 "${DEV_HOST}"
```

A cloud workspace that publishes ports under its own
`https://` names does not fit as it is: those names are
neither `*.localhost` nor the UI client's callbacks.

## 14 What Can Go Wrong

- **`js-api.localhost` does not resolve.** An old curl
  or browser. Use
  `curl --resolve js-api.localhost:8080:127.0.0.1`, or
  add the name to your hosts file
- **Every signed-in call is `401` after a restart.**
  The mock makes a new key at each start, so earlier
  tokens fail; sign in again
- **The UI's calls fail with a CORS error.** It is
  served from a port not in `ui.dev_callback_urls`;
  `make ui` serves 5173
- **The sign-in goes to Cognito, not the mock.**
  `ui/config.js` is still the live one; copy the dev
  example
- **`docs.localhost` is `404`.** `docs/_site/` is
  empty: md-preview is not installed, or the build
  failed. `md-preview build docs`
- **Port 8080, 9000 or 5432 in use.** Stop what holds
  it, or run [without containers](shared-box.md), on
  ports of your own
- **Under Podman, every service shows `(starting)`.**
  Its health checks never run without systemd; harmless
  ([rootless Podman](podman.md), §7)

## 15 See Also

- [How the project meets the box](README.md): what
  nginx decides before your code
- [Develop and change js-api](../js-api/develop.md) and
  [py-api](../py-api/develop.md): the tests, offline
