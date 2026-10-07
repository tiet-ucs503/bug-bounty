---
abstract: |
  `/users` as routes of a service you have: py-api in
  Python, or js-api in JavaScript. The door that
  records who signed in, their profile, and the people
  and roles for whoever may run them, the database
  deciding. Built in the project's five steps, with one
  contract and one set of tests for both languages.
date: 2026-10-07
keywords:
- tutorial
- py-api
- js-api
- auth
- authz
- cycle
kind: tutorial
sources:
- services/py-api/main.py
- services/js-api/server.js
- box/project.json
status: draft
subtitle: The door, the profile and the roles, in
  Python or JavaScript
title: 4 /users
version: v0.1.0
---

`[NO:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` --- what
these mean, and what they do not: [the tutorials'
page](../README.md) §5.

## 1 What You Build

Take one language. The routes, their answers and the
tests are the same in both:

- **`/users` in py-api,** FastAPI and psycopg, or **in
  js-api,** Fastify and node-postgres: the door at
  `/users/me`, the caller's own profile, the people,
  the matrix, and giving and taking roles
- **Six routes in `box/project.json`,** so nginx passes
  them
- **`test-4.sh`:** fourteen tests, written before the
  code, that call `/users` through nginx, as the UI
  will. The same file tests either language
- **The service's own tests,** which need no database
  and no network

## 2 Five Steps

This tutorial follows [the project's
cycle](../../conduct/the-cycle/README.md), one page a
step. Read them in order; at step 4, take one of the
two.

1.  **[The concept](1-concept.md).** What `/users` is
    for, as eight rules
2.  **[The contract](2-contract.md).** The routes, what
    each takes and answers, and how each refuses: what
    tutorial 6's UI relies on
3.  **[The tests](3-tests.md).** The rules as fourteen
    tests, through nginx. You run them first, and every
    one fails
4.  **The implementation,** [in
    Python](4-implementation-python.md) or [in
    JavaScript](4-implementation-javascript.md). The
    service's code, whole, and its own tests
5.  **[The refinement](5-refinement.md).** Run the
    tests, read them, and change whichever step is
    wrong

## 3 Before You Start

- [What you need](../README.md) §2, installed and
  checked
- [3 Make it a
  migration](../3-the-migration/README.md), its
  migrations applied, with `users` among the `prefixes`
  of the service you take
- A local stack, up, and the settings of [the
  tutorials' conventions](../README.md) §3 in your
  shell

## 4 See Also

- [The cycle](../../conduct/the-cycle/README.md): the
  five steps in general
- [1 Who is signed in](../1-authentication.md): the
  token, `userInfo`, and the tables `/users/me` writes
- [6 A Svelte UI](../6-a-svelte-ui/README.md): next
