---
abstract: |
  Run py-api's tests, run it on your machine, add a
  route, change a package, and get the change onto the
  box.
date: 2026-10-06
keywords:
- py-api
- tests
- build
- dependencies
kind: how-to
sources:
- services/py-api/main.py
- services/py-api/Dockerfile
- Makefile
status: draft
title: Develop and Change py-api
version: v0.1.0
---

## 1 Before You Start

- Python 3.12 on your machine
- The service's files: `main.py`, `requirements.txt`,
  `Dockerfile`, and `build.sh` and `buildspec.yml`,
  which are the box's and stay as they are

## 2 Run the Tests

Offline: the tests make a key pair and serve its public
half as the pool's keys. Expect `Ran 4 tests` and `OK`:

``` sh
cd services/py-api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt httpx && .venv/bin/python -m unittest discover -s test
```

## 3 Run It

Expect `{"status":"ok","service":"py-api"}` from
`http://localhost:8000/health`. Without the Cognito
variables, every signed-in route is `401`:

``` sh
cd services/py-api && .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

## 4 Add a Route

1.  Write it in `services/py-api/main.py`; for example:

``` python
@app.get("/items/{id}")
def item(id: str):
    return {"id": id}
```

2.  Test it, in the service's tests.
3.  Name it in `box/project.json`, with its method and
    whether it is signed in:
    `{"method": "GET", "path": "/items/{id}", "signed_in": false}`.
4.  Release it, a tag: the image is built and its
    digest recorded ([How a release reaches the
    box](../onboarding/ci-cd.md)). The new route
    answers once the box's owner has rolled the
    manifest out: [Hand a change to the box's
    owner](../onboarding/hand-over.md).

## 5 Change a Package

A package is a line in `requirements.txt` by exact
version, with each package it pulls in, as `pip freeze`
lists them on the Dockerfile's base. After an edit,
expect `No broken requirements found.`:

``` sh
cd services/py-api && .venv/bin/pip install -r requirements.txt && .venv/bin/pip check
```

## 6 Change the Base Image

By digest, in `services/py-api/Dockerfile`. Read the
new digest from `public.ecr.aws`, the index's digest,
not one architecture's: the box builds on arm64.

## 7 What Can Go Wrong

- **The build fails on the box, the tests pass here.**
  A package without an arm64 wheel or binary, or one
  installed here and not pinned; the owner can send you
  the build's log
- **`pip check` reports a conflict.** A pin was changed
  without the packages it pulls in; pin those too

## 8 See Also

- [py-api's routes](api.md)
- [Hand a change to the box's
  owner](../onboarding/hand-over.md)
