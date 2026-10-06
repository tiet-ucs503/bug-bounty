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

Access token
: The token a service reads, from the box's Cognito
  pool, sent as `Authorization: Bearer`. It carries
  `client_id`, not the email

Accessor
: A function or procedure in the database,
  `<prefix>_*`, that a service calls instead of its
  tables

Allow-list
: The box's nginx passes a request only if the manifest
  names its path and method; anything else is `404`, a
  wrong method `403`

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

Dev stack
: `make dev`: the box's nginx, your services, a mock
  sign-in, PostgreSQL and the buckets as folders, on
  your own machine

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

Pin
: Writing a new build's digest into the box's compose
  file, after which an upload and a reload run it

PKCE
: Proof Key for Code Exchange: how the UI signs in
  without a client secret, by sending a hash first and
  the secret behind it later

Prefix
: A service's part of the database: `py_api` for
  `py-api`, every object it owns named `py_api_*`

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

UI maintainer
: A user the box's owner makes for the project, for the
  rare and the urgent: it may do what a release does,
  by hand ([A release by
  hand](onboarding/release-by-hand.md)). Releases
  themselves go by the CI role

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
`shared-box`, `podman`
