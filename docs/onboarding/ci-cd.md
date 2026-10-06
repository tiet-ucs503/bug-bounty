---
abstract: |
  How a release tag reaches the box: what the workflow
  builds, syncs or hands over, by what changed since
  the tag before; the one role it works as; the record
  the box reads; and the repository's settings it
  needs.
date: 2026-10-06
keywords:
- release
- ci-cd
- github
- rollout
kind: explanation
sources:
- .github/workflows/release.yml
- .github/workflows/ci.yml
- tools/release-plan.sh
- tools/box-build.sh
- tools/release-record.sh
- box/render.py
status: draft
subtitle: A tag vX.Y.Z, and only what changed
title: How a Release Reaches the Box
version: v0.1.0
---

## 1 A Release Is a Tag

Every push and pull request runs **CI**: the manifest
and the prefixes, the services' tests, the migrations'
lint, the renders. A tag `vX.Y.Z` runs **Release**,
which runs CI first and then tells the box what changed
since the tag before it, and nothing more:

  ----------------------------------------------------
  Changed              The release
  -------------------- -------------------------------
  `services/<name>/`   Builds the service's image on
                       the box's CodeBuild; its digest
                       into the release record

  `migrations/`        Builds the migrations image;
                       its digest into the record

  `ui/`                Syncs `ui/` to `www`, its
                       config written from the
                       variables

  `docs/`              Builds the pages with
                       md-preview; syncs them to
                       `docs`

  `static/`            Adds `static/` to `static`,
                       deleting nothing

  `box/project.json`   Renders the box's pieces and
                       attaches them to the release,
                       for the box's owner
  ----------------------------------------------------

The first release does all of it. See what a tag would
do, before you push it, expecting `prev` and a line per
action:

``` sh
make plan TAG=v0.2.0
```

## 2 What the Box Does With It

``` mermaid
---
config:
  themeVariables:
    edgeLabelBackground: "#d9eaf2"
  themeCSS: ".edgeLabel, .edgeLabel p, .labelBkg { background-color: #d9eaf2 !important; color: #5c7a8a !important; }"
---
flowchart LR
  tag(["Tag vX.Y.Z"])
  gha["GitHub Actions<br/>the project's CI role"]
  cb["The box's CodeBuild<br/>the project's push role"]
  ecr[("ECR<br/>the project's images")]
  rec[("releases/name/release.json")]
  box["The box<br/>pins, migrates, reloads"]
  s3[("www, docs, static")]
  tag --> gha
  gha -->|"sources, StartBuild"| cb
  cb -->|"push, the tag"| ecr
  gha -->|"digests"| rec
  box -->|"reads"| rec
  box -->|"pulls by digest"| ecr
  gha -->|"sync"| s3
  classDef network fill:#dbeafe,stroke:#3b82f6,color:#111
  class tag,gha network
  classDef compute fill:#fff6eb,stroke:#804900,color:#804900
  class cb,box compute
  classDef storage fill:#dcfce7,stroke:#22c55e,color:#111
  class ecr,rec,s3 storage
```

- **Images:** the workflow puts a unit's folder under
  `releases/<project>/src/<unit>/` in the box's config
  bucket and starts its build with `IMAGE_TAG` the
  release's tag. The box's CodeBuild builds it, on
  arm64, and pushes it under that tag
- **The record:** `releases/<project>/release.json`,
  the tag, the commit, and every image's digest, this
  release's over the last's. The box reads it, pins the
  digests into its own copy of the project's compose
  piece, and reloads: migrations first, then the
  services
- **The buckets:** synced directly; nothing on the box
  changes

The box takes nothing from the record but digests. Its
nginx, its compose pieces and its IAM come from the box
owner's repository alone; a release cannot change them.
A change to the manifest is a hand-over: [Hand a change
to the box's owner](hand-over.md).

## 3 The One Role

`tu-rgb-sites-<project>-ci`, which the box's owner
makes from the rendered `ci-trust.json.in` and
`ci-policy.json.in`. It is assumed by GitHub's OIDC,
for this repository's `v*` tags alone, so there is no
AWS key anywhere. It may:

- put and read under `releases/<project>/` in the
  config bucket, which the box never runs
- start and read the project's own builds, and read its
  own images' digests
- sync `www` and `docs`, and add to `static` without
  deleting

## 4 The Repository's Settings

Under **Settings**, **Secrets and variables**,
**Actions**, **Variables**, from the box's owner; none
is a secret:

- `AWS_ROLE_ARN`: the CI role
- `ZONE`: the project's zone
- `COGNITO_AUTH_DOMAIN`: Cognito's sign-in domain
- `COGNITO_UI_CLIENT_ID`: the UI's client

And `"github"` in `box/project.json`: this repository,
`owner/name`, which the role's trust names.

## 5 Tag One

Expect the tag pushed, then the workflow on GitHub, its
summary listing the plan and each image's digest:

``` sh
TAG=v0.2.0
git tag -a "${TAG}" -m "${TAG}"
git push origin "${TAG}"
```

A tag is a release once: a rerun of its workflow builds
nothing already built, and reuses the digest its tag
names.

## 6 What Can Go Wrong

- **`Not authorized to perform sts:AssumeRoleWithWebIdentity`.**
  The tag is not `v*`, the repository is not the one
  the role trusts, or `AWS_ROLE_ARN` is wrong
- **A build `FAILED`.** The box's owner has its log;
  reproduce it with the image's Dockerfile on an arm64
  machine
- **The release passed, and the box still runs the old
  image.** The box reads records on its own schedule;
  ask its owner, or check the services' `/health` after
  a while
- **The manifest changed and nothing new answers.** A
  hand-over: the box's owner rolls the attached pieces
  out first

## 7 See Also

- [A release by hand](release-by-hand.md): the same
  steps, for when the CI cannot run
- [Hand a change to the box's owner](hand-over.md)
