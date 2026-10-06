---
abstract: |
  The idea the project is built on, and the conduct
  that follows from it: each piece of software here
  does one thing and does it well, and so does each
  member of the team. With the project's own examples,
  and the idioms that keep the pieces apart and the
  knowledge in one place.
date: 2026-10-06
keywords:
- conduct
- philosophy
- the-box
- release
kind: explanation
sources:
- box/render.py
- box/project.json
- tools/release-plan.sh
- tools/box-build.sh
- tools/release-record.sh
- Makefile
status: draft
subtitle: Do one thing, and do it well
title: The Philosophy
version: v0.1.0
---

## 1 One Thing, Done Well

Doug McIlroy's summary of the Unix philosophy, as Peter
H. Salus recorded it in *A Quarter Century of Unix*
(1994):

> Write programs that do one thing and do it well.
> Write programs to work together. Write programs to
> handle text streams, because that is a universal
> interface.

Every piece of software this project stands on was
chosen in that spirit, and the project's own pieces are
written in it. We take it one step further: **each
member of the team does one thing, and does it well**,
and hands it on through a contract the next one can
read.

## 2 The Pieces We Stand On

Each answers one question, and none answers another's:

  ----------------------------------------------------
  Piece         Its one thing
  ------------- --------------------------------------
  Cloudflare    The edge: certificates, the only way
                in

  nginx         The gate: which routes, which origins,
                how fast a client may write

  Cognito       Who the caller is: sign-in and tokens

  A service     What the caller may do, and doing it

  PostgreSQL    Keeping the data, and its accessors

  dbmate        Applying migrations, in order, once

  Squawk        Reading a migration for what it locks

  CodeBuild     Building an image, on arm64

  S3            Serving files

  pandoc        Converting Markdown

  md-preview    Rendering these pages

  GitHub        Running a release when a tag is pushed
  Actions       
  ----------------------------------------------------

nginx does not check tokens; a service does not answer
CORS; dbmate does not lint; Squawk does not migrate.
When one of them is replaced, the others do not notice.

## 3 The Pieces We Wrote

The same rule, in the project's own tools:

- **`box/render.py` renders.** From one manifest it
  writes the box's nginx servers, its compose piece,
  the CI role's documents and the dev stack. It never
  talks to AWS, Cloudflare or the box
- **`tools/release-plan.sh` plans.** It reads git and
  prints what a tag changes, one line an action:
  `build py-api`, `sync www`. It builds nothing and
  syncs nothing
- **`tools/box-build.sh` builds one image** and prints
  one line, its name and digest
- **`tools/release-record.sh` records.** It reads those
  lines and writes the record the box reads
- **The release workflow joins them,** as a shell joins
  programs with a pipe. Each step's output is text the
  next one reads, and that a person can read too, so
  the same steps run by hand ([A release by
  hand](../onboarding/release-by-hand.md))
- **`dev/mock-auth/server.py` stands in for Cognito's
  sign-in** and nothing more: no rights, no users kept,
  no data
- **`probes/Makefile` checks from outside,** as a user
  sees it. It has no AWS identity and needs none

## 4 The Team

The same rule for people. A member, or a small team,
owns one unit and its contract:

  ----------------------------------------------------
  Owns                 Hands on through
  -------------------- -------------------------------
  A service            Its routes in the manifest; its
                       API

  The migrations       The accessors' signatures; the
                       prefixes

  The UI               Its calls to the services'
                       routes

  The pages            `docs/`, released on its own

  The release          The tag, and the record

  The box              The rendered pieces it accepts;
                       the record's digests it pins
  ----------------------------------------------------

A person may own more than one unit, but a change does
one thing. A pull request that changes a route, a table
and the UI's look at once is three changes, three
reviews, and a harder way back.

``` mermaid
---
config:
  themeVariables:
    edgeLabelBackground: "#d9eaf2"
  themeCSS: ".edgeLabel, .edgeLabel p, .labelBkg { background-color: #d9eaf2 !important; color: #5c7a8a !important; }"
---
flowchart LR
  ui["UI"]
  svc["A service"]
  mig["Migrations"]
  box["The box"]
  rel["The release"]
  ui -->|"routes, Bearer token"| svc
  svc -->|"accessors, its prefix"| mig
  rel -->|"the record's digests"| box
  svc -.->|"the manifest"| box
  classDef compute fill:#fff6eb,stroke:#804900,color:#804900
  class ui,svc,mig,box,rel compute
```

Each arrow is a contract, written down where the other
side can read it. Nothing crosses except along one.

## 5 Cohesion and Coupling

**Cohesion:** what changes together lives together. A
service's code, its Dockerfile, its tests and its pages
change together, so they sit in its folder and its
pages' folder. A service's tables and its accessors
change together, so they share its prefix and one
migration.

**Coupling:** what is apart knows little of the other,
and only by contract.

- **A service never reads another's tables;** it calls
  the other's API. One database is shared, but by
  prefix, not by reach ([The database's
  conduct](database.md))
- **The UI knows the services by their routes,** never
  their code
- **The box and the project know each other by two
  documents alone:** the manifest, which the box's
  owner reviews, and the release record, from which the
  box takes digests and nothing else
- **A service and nginx know each other by the
  manifest's routes:** a route the code adds and the
  manifest does not name is not reachable

Loose coupling is why a service can be rewritten in
another language without the UI, the box or the other
services changing.

## 6 DRY, and Where We Copy

*Don't Repeat Yourself*, as Andy Hunt and Dave Thomas
put it in *The Pragmatic Programmer*: every piece of
knowledge has one authoritative place. It is about
knowledge, not text.

- **One manifest, many renders.** nginx's servers, the
  compose piece, the dev stack, the CI role's policy
  and the release's list of units all come from
  `box/project.json`. A route is written once
- **One list of units.** `render.py --units` is what
  the plan, the build and the check all read
- **One build script, in four folders,** on purpose.
  CodeBuild sees one folder alone, so each image's
  folder holds a copy. The knowledge is still in one
  place: `make check` refuses a copy that differs from
  `box/build.sh`
- **Each service checks its own token,** a few lines
  each in its own language, rather than a library they
  share. A shared library would couple every service to
  one release of it. Here the repetition is cheaper
  than the coupling

Repeat text when a boundary needs it; never repeat a
decision.

## 7 The Idioms Beside It

- **Single responsibility:** a unit has one reason to
  change. The migrations change for the schema, the UI
  for its users
- **Separation of concerns:** identity at Cognito, the
  gate at nginx, the rights in the service, the data in
  the database
- **Least privilege:** each piece holds what its one
  thing needs. The services' login holds rows and
  `EXECUTE`, never the schema; the CI role writes the
  release's prefix, never what the box runs; the mock
  sign-in binds to `127.0.0.1` alone
- **Fail loudly, early:** `make check` refuses a
  manifest the box would refuse, before anyone hands it
  over; a migration whose objects carry another's
  prefix never reaches the database
- **Text as the interface:** the tools print one line a
  fact, so a person, a script and a workflow read the
  same output

## 8 When to Join Things

Small is not the goal; clear is. Split when two things
change for different reasons, or at different speeds,
or for different owners. Keep together what always
changes together. The project holds one database, not
one per service, because for a small team the cost of
many outweighs the fence; a prefix keeps the fence.

## 9 See Also

- [The database's conduct](database.md): the same idea,
  in SQL
- [How a release reaches the
  box](../onboarding/ci-cd.md): the release's pieces,
  joined
- [How these pages are written](README.md): one page,
  one kind
