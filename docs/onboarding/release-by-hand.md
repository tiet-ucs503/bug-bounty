---
abstract: |
  The release workflow's steps run by hand, for
  reference and for when GitHub cannot run them: the
  plan, each image's build, the release record, and the
  syncs.
date: 2026-10-06
keywords:
- release
- rollout
kind: how-to
sources:
- tools/release-plan.sh
- tools/box-build.sh
- tools/release-record.sh
status: draft
title: A Release by Hand
version: v0.1.0
---

## 1 Before You Start

- **An identity that may do what the CI role does,**
  for this project: the box's owner gives one for the
  rare and the urgent, a user who signs in by
  `aws login`, under a profile here called `release`
- **The tag pushed** and checked out, so what is built
  is what is tagged
- `git`, `python3`, `jq`, the AWS CLI, md-preview for
  the pages

> [!WARNING]
> The record you write is what the box runs next. Build
> every image the plan names before you write it, and
> write it once.

## 2 The Plan

Expect `prev` and a line per action:

``` sh
TAG=v0.2.0
git checkout "${TAG}"
tools/release-plan.sh "${TAG}"
```

## 3 Each Image

For each `build` line, expect `<unit> sha256:...` on
the last line, and collect them:

``` sh
TAG=v0.2.0
AWS_PROFILE=release tools/box-build.sh py-api "${TAG}" | tee -a digests.txt
```

## 4 The Record

Expect `release-record: v0.2.0, images ...`:

``` sh
TAG=v0.2.0
AWS_PROFILE=release tools/release-record.sh "${TAG}" "$(git rev-parse HEAD)" digests.txt
```

## 5 The Buckets

For `sync www`, with `ui/config.js` filled in, expect
one `upload:` per changed file:

> [!CAUTION]
> `--delete` removes what the folder no longer holds.
> The previous release is the previous tag, synced
> again.

``` sh
ZONE=example.org
aws s3 sync ui/ "s3://www.${ZONE}/" --delete --exclude config.example.js --exclude config.dev.example.js --profile release
```

For `sync docs`:

``` sh
ZONE=example.org
md-preview build docs
aws s3 sync docs/_site/ "s3://docs.${ZONE}/" --delete --profile release
```

For `sync static`, deleting nothing:

``` sh
ZONE=example.org
aws s3 sync static/ "s3://static.${ZONE}/" --profile release
```

For `hand-over`, `make render` and give
`box/out/<name>/` to the box's owner.

## 6 What Can Go Wrong

- **`box-build: ... is not one of the manifest's units`.**
  A name the manifest does not hold, or `migrations`
  without `"database": true`
- **`release-plan: HEAD is not ...`.** Check the tag
  out first
- **`AccessDenied`.** The profile's session has lapsed,
  or is not the project's

## 7 See Also

- [How a release reaches the box](ci-cd.md): what each
  step is for
