---
abstract: |
  Seven tutorials, in order, that take a fork of the
  template from a sign-in to a notes dashboard with
  uploads: who comes in, what each person may do, the
  database that holds both, `/users` in py-api or
  js-api, a Svelte UI, and files in the static bucket.
  What you build, what you need, and the conventions
  every page shares.
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
  notes["py-api<br/>/users: who comes in, who may what<br/>/notes, /objects: notes and uploads"]
  db[("The project's database<br/>users_*, py_api_*")]
  bucket[("The static bucket<br/>objects/")]
  browser -->|"signs in"| cognito
  browser -->|"Bearer token"| notes
  notes -->|"userInfo: the e-mail"| cognito
  notes -->|"users_*; py_api_*, which ask users_may"| db
  notes -->|"PUT, DELETE"| bucket
  browser -->|"reads"| bucket
  classDef network fill:#dbeafe,stroke:#3b82f6,color:#111
  class cognito network
  classDef compute fill:#fff6eb,stroke:#804900,color:#804900
  class notes compute
  classDef storage fill:#dcfce7,stroke:#22c55e,color:#111
  class db,bucket storage
```

1.  [Who comes in](1-authentication.md): the rules of
    who may sign in, tried in the database
2.  [What each may do](2-authorisation/README.md): the
    access control matrix, and notes as (u=rw, a=r), in
    [the project's five
    steps](../conduct/the-cycle/README.md): concept,
    tests, contract, implementation, refinement
3.  [Make it a migration](3-the-migration.md): both as
    migrations, each proved down and up
4.  [/users in Python](4-users-in-python.md): who comes
    in, as routes of py-api, at `py-api.<zone>/users`
5.  [/users in JavaScript](5-users-in-javascript.md):
    or the same, in js-api, at `js-api.<zone>/users`
6.  [A Svelte UI](6-a-svelte-ui.md): the dashboard, who
    you are, the notes, the people
7.  [Uploads](7-uploads/README.md): files on notes, in
    the static bucket, collected when no note needs
    them

Take 4 **or** 5: the same routes, the same database, in
the language your team writes. The notes and uploads
are py-api's either way. The rest are in order; each
starts where the one before ended.

Every step on these pages was run, as written, in a
fork of the template v0.1.0. Where, and what that does
not prove, is §5; each page's badges say it in short.

## 2 What You Need

Everything every page needs is here; no page asks for
more, and each links back to this section.

- **A fork of the template,** and a shell at its root
- **A local stack,** either:
  - [the dev stack](../onboarding/local-dev.md), with
    Docker or [Podman](../onboarding/podman.md): hosts
    at `*.localhost:8080`;
  - [the native stack](../onboarding/shared-box.md),
    without containers or root: hosts at
    `*.localhost:<your NGINX_PORT>`
- **A browser,** for pages 6 and 7.4
- **Reading SQL,** and Python or JavaScript

### 2.1 Install Them

One command installs every tool, with your system's own
package manager: Arch, Debian 13, Ubuntu 24.04, Alpine
3.24 or macOS with Homebrew. It uses `sudo` unless you
are root, and checks what it installed at the end.

`make` comes first, where the system lacks it, and on
Alpine `bash`, which the Makefile runs its recipes in:

- **Debian and Ubuntu:** `sudo apt-get install make`
- **Alpine:** `sudo apk add make bash`
- **Arch and macOS:** already there

Then, from the fork's root, with the engine for your
stack. Expect every line of the check at the end to
start `ok`:

``` sh
make install-deps STACK=podman
```

- **`STACK=podman`** for [the dev
  stack](../onboarding/local-dev.md) under
  [Podman](../onboarding/podman.md)
- **`STACK=docker`** for it under Docker; on a Mac,
  Docker Desktop is yours to install
- **No `STACK`** for [the native
  stack](../onboarding/shared-box.md). Without root,
  install nothing here: that page's §2 and §3 install
  every tool below, and its own, into your home
  directory

What it does not do, since each is yours to decide:
start Docker's service, add you to the `docker` group
(§6), or start Podman's machine on a Mac. On macOS it
prints the `PATH` line to add to your shell's startup
file; open a new shell, then check (§2.3).

Tried 2026-10-06 in containers of Arch, Debian 13,
Ubuntu 24.04 and Alpine 3.24: every tool installed and
checked, then `make check` and `make test` passing.
macOS's recipe is written but not yet tried.

### 2.2 What It Installs, and Why

- **`git`, `bash` and GNU `make`:** every page. The
  Makefile is the way in: `make check`,
  `make dev-token`, `make test`, `make ui`
- **`curl` and `jq` 1.6 or later:** every page
- **Python 3.12 or later:** the render behind
  `make check` and `make dev`, tutorial 4's
  `make test`, and the test image 7.3 draws
- **`psql` and `pg_dump`, PostgreSQL 17 or later:**
  tutorials 1, 2, 3 and 7.2. `pg_dump` refuses a server
  newer than itself, and the stack's is 17. Debian and
  Ubuntu get them from PostgreSQL's own repository
- **`openssl` and `base64`:** 7.1, a file's SHA-256 as
  S3 wants it
- **Node 24 or later, with `npm`:** tutorial 3, for
  Squawk by `npx`; 5, 6 and 7.4. Debian and Ubuntu get
  it from NodeSource's repository
- **`diff`, `cmp` and `grep`:** tutorials 3 and 7.3
- **With `STACK`:** Docker with Compose 2.20 or later,
  or Podman 5 with podman-compose 1.5. dbmate and the
  database run in the stack's containers, so `make db`
  needs nothing more

Debian 13's podman-compose is 1.3, and Ubuntu 24.04's
Podman 4.9 with podman-compose 1.0.6: older than the
stack was tried with. The check says so; take Podman
from conda-forge instead, [Podman's
page](../onboarding/podman.md) §2.

### 2.3 Check Them

At any time, the same check `install-deps` ends with.
Expect every line to start `ok`; `old` or `none` names
the tool to install or update:

``` sh
make check-deps STACK=podman
```

Security notes on these tools are §6.

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

For the native stack, `H` and `MOCK_URL` come from your
own ports, and `env.sh` sets the other four itself:
`MIGRATOR_URL`, `DATABASE_URL`, `STORE_URL` and
`STATIC_URL`.

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
- **One thing, done well,** a unit each, by its prefix
  in the database: `users` for people and roles,
  `py_api` for notes and uploads. One service may run
  both, py-api here, each with names of its own. [The
  philosophy](../conduct/philosophy.md)

## 5 Where These Pages Ran

### 5.1 The Badges

Each tutorial carries a badge for each stack, below its
title, and in [the map](../README.md) §3 beside its
status:

- **`[OK:NATIVE]`:** every step run as written, on that
  stack, at the page's version, and every answer the
  page's
- **`[NO:NATIVE]`:** not so: never run there, run only
  in part, not since the page last changed, or failed
- **`NATIVE`, `PODMAN`, `DOCKER`:** [the native
  stack](../onboarding/shared-box.md); [the dev
  stack](../onboarding/local-dev.md) under [rootless
  Podman](../onboarding/podman.md); the dev stack under
  [Docker](../onboarding/local-dev.md), its default
  (§1 there)

A badge is a record of a run, not a promise: a page
changed since its run goes back to `NO`.

  -----------------------------------------------------
  Tutorial                  Badges
  ------------------------- ---------------------------
  1 Who comes in            `[OK:NATIVE]` `[NO:PODMAN]`
                            `[NO:DOCKER]`

  2 What each may do        `[OK:NATIVE]` `[NO:PODMAN]`
                            `[NO:DOCKER]`

  3 Make it a migration     `[OK:NATIVE]` `[NO:PODMAN]`
                            `[NO:DOCKER]`

  4 /users in Python        `[OK:NATIVE]` `[NO:PODMAN]`
                            `[NO:DOCKER]`

  5 /users in JavaScript    `[OK:NATIVE]` `[NO:PODMAN]`
                            `[NO:DOCKER]`

  6 A Svelte UI             `[OK:NATIVE]` `[NO:PODMAN]`
                            `[NO:DOCKER]`

  7 Uploads                 `[OK:NATIVE]` `[NO:PODMAN]`
                            `[NO:DOCKER]`
  -----------------------------------------------------

### 5.2 Where They Ran

- **The native stack,** without root, in a fork of the
  template: every step of every page. Tutorial 2's
  tests 2026-10-07, before and after its code, and with
  its code broken on purpose; the rest 2026-10-06
- **The dev stack under rootless Podman,** the same
  fork, 2026-10-06, in part: every image built, the
  door, the notes, an upload read back through nginx,
  the collector. Not every step of every page, and not
  since `/users` moved into py-api and js-api, so `NO`
- **Docker:** not yet
- **The dashboard,** tutorials 6 and 7.4, in a headless
  Chromium: the sign-in, a role granted, notes added
  and edited, files chosen and dropped
- **Every code block** on the pages is the file that
  ran, checked by a script, character for character

### 5.3 What Stood In for the Box

- **Cognito:** the mock sign-in, `dev/mock-auth/`: its
  endpoints, its tokens' shapes, and a `userInfo` that
  answers the e-mail you gave
- **The static bucket:** a folder, behind the mock
  store, for `objects/`
- **The database:** PostgreSQL 17 on your own machine
- **nginx:** the box's servers, rendered from the
  manifest as the box renders them, on plain HTTP at
  `*.localhost`
- **Cloudflare:** nothing; no edge, no TLS, no rate
  rules

### 5.4 Why They Cannot Yet Run on the Box

The box does not yet take a project. Its half is being
built: the points where nginx and Compose include a
project's pieces, the repositories, buckets and sign-in
client each project gets, the right to pull its images,
and the grants tutorial 7 needs on the static bucket
(§5 of [its overview](7-uploads/README.md)). And the
box's own database is MariaDB until it moves to
PostgreSQL, which these pages assume.

### 5.5 What Only the Box Can Show

- **Cognito itself:** a real sign-in, its Google users,
  and its `userInfo`. The mock was written from AWS's
  documents, not from AWS's answers
- **S3:** a path-style `PUT` and `DELETE` from the
  box's address, and what the bucket's policy refuses
- **Cloudflare in front:** TLS, the size rule, and the
  rate rule on `/objects/`
- **A release:** the CI role, the builds, and the box
  reading what a release records

## 6 The Tools' Security

None of these tools is unusual, but each of the
following trusts something, or gives something, that
you should know about.

> [!WARNING]
> **The `docker` group is root.** A member can start a
> container that mounts `/` and writes to it, with no
> password asked. Adding yourself to the group, which
> many install guides suggest, gives root to anything
> that runs as you. Prefer [rootless
> Podman](../onboarding/podman.md) or Docker's own
> rootless mode, or keep `sudo docker` and accept the
> prompt.

- **`make install-deps` runs your package manager as
  root,** by `sudo`, and installs only what its recipe
  names. Read the recipe for your system in the
  Makefile first; it is a few lines
- **On Debian and Ubuntu it adds two apt
  repositories,** and root then trusts each for the
  packages it serves. PostgreSQL's key is the one your
  system's own `postgresql-common` ships, so it comes
  through your distribution's signatures. NodeSource's
  is fetched, and refused unless its fingerprint is
  `6F71F525282841EEDAF851B42F59B5F99B1BE0B4`. That is
  the key as first read, 2026-10-06, not one NodeSource
  publishes elsewhere: it catches a key changed since,
  not a bad one then. The recipe never pipes a maker's
  script into `sudo bash`, as many install guides do
- **`npm` runs packages' code as you,** at install as
  well as at run: `npm ci` and `npm install` run their
  install scripts, and `npx --yes squawk-cli@2.67.0`
  fetches and runs a package, its binary in a second
  package for your platform. Versions are pinned and
  lockfiles committed, which stops a surprise upgrade,
  not a bad release
- **`pip` installs into each service's own `.venv`,**
  never system-wide, from PyPI by the versions in its
  `requirements.txt`, without hashes; `make test` adds
  `httpx`, unpinned. A package with no wheel for your
  platform is built from source, which runs its code
- **micromamba is fetched unchecked,** by `curl` into
  `tar`, from its own site, and it trusts conda-forge
  for every package it installs. [The native stack's
  page](../onboarding/shared-box.md) §3 checks dbmate's
  SHA-256 against its GitHub release. That catches a
  corrupt download, but not a release replaced at
  GitHub, since the hash comes from the same place
- **The mocks admit anyone, on `127.0.0.1`.** On a
  shared machine every user can reach them, and the
  database's URL, password and all, is visible in `ps`
  while `psql` or `pg_dump` runs. Use a password of
  your own, and only test data: [the native stack's
  page](../onboarding/shared-box.md) §1 and §5
- **Podman's `newuidmap` and `newgidmap` are setuid
  root,** installed by the administrator. They map only
  the IDs that `/etc/subuid` and `/etc/subgid` give you

## 7 See Also

- [The database's conduct](../conduct/database.md):
  prefixes, accessors, and the one function a unit
  publishes
- [Write a
  migration](../migrations/write-a-migration.md)
- [The UI](../ui/README.md)
