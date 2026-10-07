---
abstract: |
  A dashboard in Svelte: who you are and your profile,
  from `/users/me`; every note, yours to change and the
  rest to read; and, for whoever may run them, the
  people and their roles. py-api's notes routes first,
  then `ui/` as a Svelte project, its sign-in carried
  over from the starter. Built in the project's five
  steps.
date: 2026-10-07
keywords:
- tutorial
- ui
- svelte
- py-api
- cycle
kind: tutorial
sources:
- ui/app.js
- services/py-api/main.py
- .github/workflows/release.yml
- Makefile
status: draft
subtitle: The notes, the profile and the people, in a
  browser
title: 5 A Svelte UI
version: v0.1.0
---

`[NO:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` --- what
these mean, and what they do not: [the tutorials'
page](../README.md) §5.

## 1 What You Build

- **py-api's notes routes,** over tutorial 3's
  accessors: list, add, edit and delete, the database
  deciding
- **`ui/` as a Svelte project,** built by Vite: the
  starter's sign-in carried over, then a dashboard of
  four parts, each shown by what `/users/me` says you
  may do: your profile, the notes, and the people
- **`test-5.sh`:** thirteen tests, written before the
  code: six call the notes through nginx; seven render
  the dashboard in `ui/`'s own tests, with no browser
  and no network

## 2 Five Steps

This tutorial follows [the project's
cycle](../../conduct/the-cycle/README.md), one page a
step. Read them in order.

1.  **[The concept](1-concept.md).** What the notes
    routes and the dashboard are for, as ten rules
2.  **[The contract](2-contract.md).** The notes
    routes, and what the dashboard relies on: `/users`,
    and its `config.js`
3.  **[The tests](3-tests.md).** The rules as thirteen
    tests. You run them first, and every one fails
4.  **[The implementation](4-implementation.md).** The
    routes in py-api, the Svelte project, the sign-in,
    and the dashboard's five components
5.  **[The refinement](5-refinement.md).** Run the
    tests, read them, and change whichever step is
    wrong

## 3 Before You Start

- [What you need](../README.md) §2, installed and
  checked
- [4 /users](../4-users/README.md), in py-api or
  js-api, running, and `test-4.sh` passing
- The settings of [the tutorials'
  conventions](../README.md) §3 in your shell
- [Svelte 5's
  runes](https://svelte.dev/docs/svelte/overview), in
  passing: `$state` for what changes, `$props` for what
  a component is given

## 4 See Also

- [The cycle](../../conduct/the-cycle/README.md): the
  five steps in general
- [The UI](../../ui/README.md): what the box asks of
  any UI
- [6 Uploads](../6-uploads/README.md): next
