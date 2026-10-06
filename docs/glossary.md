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
- box/how-the-box-works.md
status: draft
title: Glossary
version: v0.1.0
---

## 1 Terms

Access token
: The token a service reads, from the box's Cognito
  pool, sent as `Authorization: Bearer`. It carries
  `client_id`, not the email

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

Render
: `make render`: the box's pieces, written from the
  manifest into `box/out/<name>/`

UI maintainer
: The role or user the box's owner makes for the
  project, which may write the `www` and `docs` buckets
  and nothing else

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
`db`
