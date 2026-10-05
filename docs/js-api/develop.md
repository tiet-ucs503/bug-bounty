---
abstract: |
  Run js-api's tests, run it on your machine, add a
  route, change a package, and get the change onto the
  box.
date: 2026-10-06
keywords:
- js-api
- tests
- build
- dependencies
kind: how-to
sources:
- services/js-api/server.js
- services/js-api/Dockerfile
- Makefile
status: draft
title: Develop and Change js-api
version: v0.1.0
---

## 1 Before You Start

- Node 24 on your machine
- The service's files: `server.js`, `package.json`,
  `package-lock.json`, `Dockerfile`, and `build.sh` and
  `buildspec.yml`, which are the box's and stay as they
  are

## 2 Run the Tests

Offline: the tests make a key pair and serve its public
half as the pool's keys. Expect `ℹ pass 4` and
`ℹ fail 0`:

``` sh
cd services/js-api && npm ci && npm test
```

## 3 Run It

Expect `{"status":"ok","service":"js-api"}` from
`http://localhost:3000/health`. Without the Cognito
variables, every signed-in route is `401`:

``` sh
cd services/js-api && npm ci && PORT=3000 node server.js
```

## 4 Add a Route

1.  Write it in `services/js-api/server.js`; for
    example:

``` js
app.get("/items/:id", async (req) => ({ id: req.params.id }));
```

2.  Test it, in the service's tests.
3.  Name it in `box/project.json`, with its method and
    whether it is signed in:
    `{"method": "GET", "path": "/items/{id}", "signed_in": false}`.
4.  Render and hand over: [Hand a change to the box's
    owner](../onboarding/hand-over.md).

## 5 Change a Package

A package is a line in `package.json` by exact version,
and the lockfile written by npm. Expect
`package-lock.json` changed and `make check` passing:

``` sh
cd services/js-api && npm install --save-exact --no-fund --no-audit fastify@5.12.5
```

The image installs the lockfile alone,
`npm ci --omit=dev`; a package missing from it fails
the build.

## 6 Change the Base Image

By digest, in `services/js-api/Dockerfile`. Read the
new digest from `public.ecr.aws`, the index's digest,
not one architecture's: the box builds on arm64.

## 7 What Can Go Wrong

- **The build fails on the box, the tests pass here.**
  A package without an arm64 wheel or binary, or one
  installed here and not pinned; the owner can send you
  the build's log
- **`make check` says the lockfile differs.**
  `package.json` changed without `npm install`

## 8 See Also

- [js-api's routes](api.md)
- [Hand a change to the box's
  owner](../onboarding/hand-over.md)
