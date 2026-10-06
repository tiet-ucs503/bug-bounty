---
abstract: |
  The terms these pages use, each in a line or two, and
  the keywords in use in their frontmatter.
date: 2026-10-06
keywords:
- glossary
- terms
kind: reference
sources:
- box/project.json
- docs/onboarding/README.md
status: draft
title: Glossary
version: v0.1.0
---

## 1 Terms

Access control matrix
: Roles by permissions, a cell for each yes, kept in
  the database as `users_grants`. Nothing is allowed
  unless a role a person holds says so

Access token
: The token a service reads, from the box's Cognito
  pool, sent as `Authorization: Bearer`. It carries
  `client_id`, not the email

Accessor
: A function or procedure in the database,
  `<prefix>_*`, that a service calls instead of its
  tables

Admission
: Whether a signed-in person may come into the project:
  the first rule, by position, whose pattern their
  verified e-mail matches, read at their first sign-in.
  No match, no entry

Allow-list
: The box's nginx passes a request only if the manifest
  names its path and method; anything else is `404`, a
  wrong method `403`

Badge
: `[OK:NATIVE]`, `[NO:PODMAN]` and the like, under a
  tutorial's title: whether every step ran as written
  on that stack, at the page's version

Box
: The shared host the project runs on: one arm64 EC2
  instance behind Cloudflare, with nginx, Docker and
  the buckets around it. Its owner keeps it in another
  repository

Box's owner
: Whoever keeps the box. They review and roll out what
  the project hands over

CI role
: `tu-rgb-sites-<project>-ci`, the one role a release
  works as, assumed by GitHub's OIDC for the
  repository's `v*` tags alone

Collector
: py-api's thread that deletes from the static bucket
  the objects no note has referred to for a grace, then
  forgets them

Concept
: Step 1 of the cycle: what a feature is for, for whom,
  its rules, what it will not do, and one artefact that
  holds them. The source of truth until the contract
  exists. [The concept](conduct/concept.md)

Contract
: Step 3 of the cycle: what a feature promises other
  people, exactly: routes and answers, accessors'
  signatures and refusals. Changed by adding beside,
  never in place. [The cycle](conduct/the-cycle.md) §2

Cycle
: The five steps a feature is built in, in turns:
  concept, tests, contract, implementation, refinement.
  [The cycle](conduct/the-cycle.md)

deny-all
: The role that grants nothing: whoever holds it alone
  is in, and may do nothing. Where everyone starts, by
  the template's default rule

Dev stack
: `make dev`: the box's nginx, your services, a mock
  sign-in, PostgreSQL and the buckets as folders, on
  your own machine

dev/dev.env
: `KEY=value` settings of your own, read by every
  service in the dev stack and the native stack;
  ignored by git

Digest
: An image's `sha256:` name. The box pulls images by
  digest alone, so what runs is exactly what was built

Manifest
: `box/project.json`: the project's name, its services
  and their routes, as the box sees them

Migration
: One change to the project's database: a file in
  `migrations/sql/` named for its service's prefix, its
  up and its down, applied by dbmate

Migrations image
: dbmate and every migration,
  `tu-rgb-sites-<project>-migrations`, which the box
  runs once before the services at every start

Migrator
: `<project>_migrator`, the login that owns the
  database's schema and runs the migrations; the
  services' login, `<project>`, holds rows and
  `EXECUTE` alone

Mock sign-in
: `mock-auth`, the dev stack's stand-in for Cognito:
  its endpoints and token shapes, admitting anyone

Mock store
: The dev stack's stand-in for the static bucket's
  `objects/`: S3's unsigned writes and checksum check,
  read through nginx

Object
: An upload, in the static bucket under
  `objects/<owner's tag>/<SHA-256>`: one owner's, never
  overwritten, read by anyone at `static.<zone>`

Permission
: `<unit>.<verb>`, such as `notes.write`: a column of
  the access control matrix, named for the unit that
  asks for it

Pin
: Writing a new build's digest into the box's compose
  file, after which an upload and a reload run it

PKCE
: Proof Key for Code Exchange: how the UI signs in
  without a client secret, by sending a hash first and
  the secret behind it later

Prefix
: A unit's part of the database: `py_api` for `py-api`,
  every object it owns named `py_api_*`. A service owns
  one, or several by `prefixes` in the manifest, as
  py-api holding `/users` owns `users` too

Published function
: A unit's function that other units may call, marked
  `published:` in its comment, its signature a promise.
  `users_may` is the one the template's tutorials make

Refinement
: Step 5 of the cycle: run the tests, read them, and
  change whichever step is wrong, the concept, the
  tests or the contract as well as the code

Release
: A tag `vX.Y.Z`: images built for what changed,
  buckets synced, and a release record written

Release record
: `releases/<project>/release.json` in the box's config
  bucket: the tag, the commit and every image's digest,
  which the box pins from

Render
: `make render`: the box's pieces, written from the
  manifest into `box/out/<name>/`

Role
: A row of the access control matrix. A person holds
  any number; their rights are the union

Test ID
: `T<feature>.<n>`, such as `T2.12`: a test's name on
  its tests page and in its code, so a failure names
  the rule it breaks

UI maintainer
: A user the box's owner makes for the project, for the
  rare and the urgent: it may do what a release does,
  by hand ([A release by
  hand](onboarding/release-by-hand.md)). Releases
  themselves go by the CI role

Unit
: One thing the project does, with a prefix of its own
  in the database: its tables, accessors and
  migrations. A service runs one unit or several:
  py-api runs `py_api` and, after tutorial 4, `users`

userInfo
: Cognito's endpoint that answers a person's e-mail and
  `email_verified`, a string, to their own access token

Zone
: The domain the project's hosts sit under, one label
  each: `www.<zone>`, `docs.<zone>`, `<service>.<zone>`

## 2 Keywords in Use

`overview`, `audience`, `map`, `glossary`, `terms`,
`writing`, `template`, `frontmatter`, `diataxis`,
`md-preview`, `masking`, `the-box`, `nginx`,
`cloudflare`, `manifest`, `render`, `rollout`,
`hand-over`, `release`, `ui`, `docs`, `probes`,
`js-api`, `py-api`, `api`, `routes`, `auth`, `cognito`,
`tests`, `build`, `dependencies`, `local-dev`, `mock`,
`db`, `migration`, `dbmate`, `squawk`, `postgres`,
`ci-cd`, `github`, `conduct`, `philosophy`,
`shared-box`, `podman`, `tutorial`, `admission`,
`authz`, `acm`, `svelte`, `uploads`, `static`, `s3`,
`node`, `python`, `concept`, `cycle`, `contract`,
`workflow`, `git`, `git-flow`, `identity`, `naming`
