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
- **`jq` and `curl`;** Python 3 for the render;
  md-preview, if you want these pages at
  `docs.localhost`
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
  db[("PostgreSQL<br/>localhost:5432")]
  files[("Folders<br/>static, docs")]
  browser -->|"signs in"| auth
  browser -->|"Bearer token"| nginx
  nginx --> svc
  nginx --> files
  svc -->|"the pool's keys"| auth
  svc -.->|"DATABASE_URL"| db
  classDef network fill:#dbeafe,stroke:#3b82f6,color:#111
  class auth network
  classDef compute fill:#fff6eb,stroke:#804900,color:#804900
  class nginx,svc compute
  classDef storage fill:#dcfce7,stroke:#22c55e,color:#111
  class db,files storage
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

  Cognito, the box's   `mock-auth`: the same endpoints
  pool                 and token shapes, a key made at
                       start, any name admitted

  No database yet      PostgreSQL 17, `DATABASE_URL`
                       given to every service

  `static` and `docs`  Folders, read-only:
  buckets              `dev/static/`, `docs/_site/`

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
TOKEN=$(make -s dev-token SUB=alice GROUPS=admin)
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

The box has no database yet; the stack has one, so a
service can be readied for it. Each service has
`DATABASE_URL` in its environment. From your machine,
expect a `psql` prompt:

``` sh
psql postgres://example:dev-only@localhost:5432/example
```

The user and database are your project's `name`. The
data lives in the stack's volume, `db`, between runs.

## 7 Read the Buckets

Expect the sample file's text, and then these pages:

``` sh
curl -s http://static.localhost:8080/hello.txt
curl -s -o /dev/null -w '%{http_code}\n' http://docs.localhost:8080/
```

Put what your UI reads from `static.<zone>` in
`dev/static/`. Writes to `static` are not wired on the
box, so the folder is read-only here too.

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
  as it is

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

## 10 Without Docker

The services and the mock run on your machine alone,
with no nginx: no allow-list and no CORS, so `curl` and
the tests only. With the mock's packages installed,
`dev/mock-auth/requirements.txt`:

``` sh
python3 dev/mock-auth/server.py
```

Then start a service with
`COGNITO_ISSUER=http://localhost:9000`,
`COGNITO_UI_CLIENT_ID=dev-ui` and
`COGNITO_PROBE_CLIENT_ID=dev-probe`, as [its
development page](../js-api/develop.md) shows.

## 11 What Can Go Wrong

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
  it, or change the port in `box/render.py`'s dev
  render

## 12 See Also

- [How the project meets the box](README.md): what
  nginx decides before your code
- [Develop and change js-api](../js-api/develop.md) and
  [py-api](../py-api/develop.md): the tests, offline
