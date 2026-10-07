---
abstract: |
  How a new UI reaches www: a release tag whose changes
  include ui/, synced by the project's CI role, with
  nothing built or reloaded on the box.
date: 2026-10-06
keywords:
- ui
- release
kind: how-to
sources:
- .github/workflows/release.yml
status: draft
title: Release the UI
version: v0.1.0
---

## 1 Before You Start

- The change on the default branch, its checks passing
- The repository's variables set: `ZONE`,
  `COGNITO_AUTH_DOMAIN` and `COGNITO_UI_CLIENT_ID`
  ([How a release reaches the
  box](../onboarding/ci-cd.md))

## 2 Tag a Release

A tag whose changes since the tag before include `ui/`.
Expect the tag pushed, and the workflow **Release**
started on GitHub:

``` sh
TAG=v0.2.0
git tag -a "${TAG}" -m "${TAG}"
git push origin "${TAG}"
```

The workflow writes `ui/config.js` from the variables
and syncs `ui/` to `www`, deleting what `ui/` no longer
holds. It runs after any image the same release builds,
so the UI never calls an API the box has not been told
of.

## 3 Check

Expect `PASS`:

``` sh
make -C probes www ZONE=example.org
```

## 4 Another Build of the UI

A `ui/package.json` is the sign: the job **www** in
`.github/workflows/release.yml` runs `npm ci` and
`npm run build`, writes `config.js` into `ui/dist/`,
and syncs that folder instead of `ui/`; CI builds it on
every push. A framework that builds elsewhere: change
the job to sync that folder. The bucket expects static
files with `index.html` at the root. [A Svelte
UI](../tutorials/6-a-svelte-ui/README.md) is the worked
case.

## 5 What Can Go Wrong

- **The old page still shows.** Cloudflare caches by
  file extension. Name assets by their content's hash,
  or ask the box's owner to purge
- **The job fails, `ZONE ... unset`.** A repository
  variable is missing
- **`AccessDenied` on the sync.** The CI role does not
  name this zone's `www`; the box's owner has its
  policy

## 6 See Also

- [How a release reaches the
  box](../onboarding/ci-cd.md)
- [A release by
  hand](../onboarding/release-by-hand.md): when the CI
  cannot
