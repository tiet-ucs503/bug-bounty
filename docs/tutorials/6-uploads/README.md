---
abstract: |
  Files on notes. Each upload an object in the
  project's static bucket, under `objects/`, read by
  anyone at `static.<zone>` and written only through
  py-api; its key names its owner and its content, so
  it is never overwritten; each note's references to it
  counted, and an object no note needs collected after
  a grace. Built in the project's five steps, its
  implementation in four parts: the store, the
  database, the service, the UI.
date: 2026-10-07
keywords:
- tutorial
- uploads
- static
- s3
- py-api
- cycle
kind: tutorial
sources:
- dev/mock-store/server.py
- box/render.py
status: draft
subtitle: Files on notes, in the static bucket
title: 6 Uploads
version: v0.1.0
---

`[NO:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` --- what
these mean, and what they do not: [the tutorials'
page](../README.md) §5.

## 1 What You Build

- **A permission,** `objects.write`, for members, and
  **py-api's objects** in the database: their owners,
  the notes' references, and what may be collected
- **Three routes in py-api:** an upload, your uploads,
  and a note's list of them; and a collector, which
  deletes what no note needs
- **Attachments in the dashboard:** a file selector,
  then drag and drop, each checked before it is sent
- **`test-6.sh`, `test-6.sql` and
  `ui/test/attach.test.js`:** eighteen tests, written
  before the code

## 2 Five Steps

This tutorial follows [the project's
cycle](../../conduct/the-cycle/README.md), one page a
step, step 4 in four parts. Read them in order.

1.  **[The concept](1-concept.md).** Where uploads
    live, who reads and writes them, how they are
    named, and how they go, as seven rules
2.  **[The contract](2-contract.md).** The routes, the
    accessors, the store's behaviour, and what the box
    must give
3.  **[The tests](3-tests.md).** The rules as eighteen
    tests. You run them first, and every one fails
4.  **The implementation,** in four parts:
    1.  [The store](4-the-store.md): the static
        bucket's `objects/` on your machine
    2.  [The database](4-the-database.md): objects,
        owners, references and the grace
    3.  [The service](4-the-service.md): upload, link,
        collect
    4.  [The UI](4-the-ui.md): from a file selector to
        drag and drop
5.  **[The refinement](5-refinement.md).** Run the
    tests, read them, and change whichever step is
    wrong. One refinement made while this tutorial was
    written, shown whole: to tutorial 5's tests

## 3 Before You Start

- [What you need](../README.md) §2, installed and
  checked
- [5 A Svelte UI](../5-a-svelte-ui/README.md): the
  notes, in py-api and in the dashboard, and
  `test-5.sh` passing
- A local stack whose render has the mock store:
  `make dev`, or the native stack's `start`, after this
  template's v0.1.0
- The settings of [the tutorials'
  conventions](../README.md) §3 in your shell, all six

## 4 See Also

- [The cycle](../../conduct/the-cycle/README.md): the
  five steps in general
- [The database's conduct](../../conduct/database.md)
- [The tutorials](../README.md): the whole path
