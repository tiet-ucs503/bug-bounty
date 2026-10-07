---
abstract: |
  Step 4 of tutorial 6, part 1. The static bucket's
  `objects/` on your machine: a mock of S3 that takes
  an unsigned write, checks its checksum as S3 does,
  and serves the object back through the stack's nginx
  at `static.localhost`. Write one by hand, read it,
  see a bad checksum refused, and see that nothing
  writes through the static host.
date: 2026-10-06
keywords:
- tutorial
- uploads
- static
- s3
- mock
kind: tutorial
sources:
- dev/mock-store/server.py
- box/render.py
status: draft
subtitle: S3's part, mocked, and what it refuses
title: "6.4 Uploads: the Store"
version: v0.1.0
---

## 1 Before You Start

- [What you need](../README.md) §2, installed and
  checked
- [The tests](3-tests.md), saved and failing
- A local stack up, and [the conventions](../README.md)
  §3 set, `STORE_URL` and `STATIC_URL` among them

## 2 What Stands In for the Bucket

  ----------------------------------------------------------
  On the box                  Here
  --------------------------- ------------------------------
  `PUT` to S3's path-style    `PUT` to `mock-store`, the
  address, from the box's     same path:
  Elastic IP, unsigned        `/<bucket>/objects/<key>`

  S3 matches the body to      The same check, the same
  `x-amz-checksum-sha256`,    refusal
  refusing `BadDigest`        

  Reads at                    Reads at
  `static.<zone>/objects/`,   `static.localhost/objects/`,
  through Cloudflare          through the stack's nginx,
                              which passes `GET` alone

  The bucket's other keys,    `static/`, from the folder, as
  from `static/` by a release before
  ----------------------------------------------------------

The mock takes keys under `objects/` alone, and anyone
who reaches it may write: it listens on your machine
only.

## 3 Write One by Hand

A small file, and its checksum as S3 wants it, the
SHA-256 in base64:

``` sh
printf 'hello, objects\n' > /tmp/hello.txt
SUM=$(openssl dgst -sha256 -binary /tmp/hello.txt | base64)
```

Put it under a key of your choosing. Expect `200`:

``` sh
curl -s -o /dev/null -w '%{http_code}\n' -X PUT -H 'Content-Type: text/plain' -H "x-amz-checksum-sha256: ${SUM}" --data-binary @/tmp/hello.txt "${STORE_URL}/objects/try/hello"
```

## 4 Read It Back

Through nginx, as a browser would. Expect `200`, the
type it was stored with, and the text:

``` sh
curl -s -D - "${STATIC_URL}/objects/try/hello" | grep -iE '^(HTTP|content-type)|hello'
```

## 5 What It Refuses

A body that does not match its checksum. Expect `400`
and `BadDigest`:

``` sh
curl -s -w ' %{http_code}\n' -X PUT -H "x-amz-checksum-sha256: ${SUM}" --data-binary 'other bytes' "${STORE_URL}/objects/try/hello"
```

A write through the static host. Expect nginx's `403`:

``` sh
curl -s -o /dev/null -w '%{http_code}\n' -X PUT --data-binary x "${STATIC_URL}/objects/try/hello"
```

A key outside `objects/`. Expect `404` and `NoSuchKey`:

``` sh
curl -s -w ' %{http_code}\n' -X PUT --data-binary x "${STORE_URL}/hello"
```

## 6 Delete It

Expect `204`, then `404` from nginx:

``` sh
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE "${STORE_URL}/objects/try/hello"
curl -s -o /dev/null -w '%{http_code}\n' "${STATIC_URL}/objects/try/hello"
```

A delete of what is not there is `204` too, as S3's:
the collector may delete twice without harm.

## 7 What Can Go Wrong

- **`Connection refused` on `STORE_URL`.** The stack's
  render is older than the mock store: `make dev`
  again, or the native stack's `stop` and `start`
- **`502` on `STATIC_URL/objects/...`.** nginx is up
  but the mock store is not:
  `tools/native-dev.sh status`, or `docker compose ps`
- **Your uploads vanish at `make dev-down`.** They do
  not: the store is a volume, as the database is. A
  `down -v` takes both

## 8 See Also

- [The database](4-the-database.md): next
- [S3's checks of an object's
  integrity](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html),
  read 2026-10-06
